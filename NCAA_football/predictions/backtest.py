"""
Walk-forward backtest for the Bayesian NCAAF spread model.

Procedure (no leakage — every prediction uses only prior information):
  1. Burn-in (2010-2014): fit the feature scaler, then assimilate every week
     sequentially to initialise the posterior.
  2. Evaluation (2015-2024), season by season, week by week IN ORDER:
        a. PREDICT every game in the week with the current posterior.
        b. Record predictions vs. actual results.
        c. UPDATE the posterior with that week's completed games.
        d. At each season boundary apply the season discount (re-inflation).

Outputs:
  predictions/predictions/predictions_{season}.csv   per-game predictions
  predictions/accuracy/season_accuracy.csv           one row per season
  predictions/accuracy/calibration.csv               win-prob calibration bins
  predictions/accuracy/backtest_summary.json         headline metrics
  predictions/model_state/model_after_{season}.json  posterior snapshots
"""

import os
import json
import numpy as np
import pandas as pd

import features as F
from model import BayesianSpreadModel
import config as C


def _predict_week_df(model, season, week):
    X, meta = F.build_week_matrix(season, week, fbs_only=C.FBS_ONLY)
    if len(meta) == 0:
        return pd.DataFrame()
    out = model.predict(X)
    meta = meta.copy()
    meta["pred_spread"] = out["pred_spread"]
    meta["win_prob_home"] = out["win_prob_home"]
    meta["pp_scale"] = out["pp_scale"]
    meta["pred_winner"] = np.where(meta["pred_spread"] >= 0,
                                   meta["home_team"], meta["away_team"])
    meta["pred_win_prob"] = np.where(meta["pred_spread"] >= 0,
                                     meta["win_prob_home"], 1 - meta["win_prob_home"])
    return meta


def _assimilate_week(model, season, week):
    X, meta = F.build_week_matrix(season, week, fbs_only=C.FBS_ONLY)
    if len(meta) == 0:
        return
    mask = meta["completed"].values
    if mask.sum() == 0:
        return
    model.update(X[mask], meta.loc[mask, "actual_spread"].values)


def run_backtest():
    model = BayesianSpreadModel()

    # ---- 1. burn-in: fit scaler then assimilate sequentially -------------
    Xb, _ = F.build_dataset(C.BURN_IN_SEASONS, completed_only=True, fbs_only=C.FBS_ONLY)
    if len(Xb) == 0:
        raise RuntimeError("No burn-in data found.")
    model.fit_scaler(Xb)
    for s in C.BURN_IN_SEASONS:
        for w in F.season_weeks(s):
            _assimilate_week(model, s, w)
        model.discount(C.SEASON_DISCOUNT)
    print(f"Burn-in complete: {model.n_obs} games assimilated, "
          f"sigma~{np.sqrt(model.sigma2_hat):.1f} pts")

    # ---- 2. walk-forward evaluation --------------------------------------
    all_preds = []
    for s in C.EVAL_SEASONS:
        weeks = F.season_weeks(s)
        for w in weeks:
            preds = _predict_week_df(model, s, w)          # predict first
            if len(preds):
                all_preds.append(preds)
            if C.WEEKLY_DISCOUNT < 1.0:
                model.discount(C.WEEKLY_DISCOUNT)
            _assimilate_week(model, s, w)                  # then learn
        model.save(os.path.join(C.STATE_DIR, f"model_after_{s}.json"))
        model.discount(C.SEASON_DISCOUNT)                  # season re-inflation

    preds = pd.concat(all_preds, ignore_index=True)
    # Save per-season prediction files.
    for s, grp in preds.groupby("season"):
        grp.to_csv(os.path.join(C.PRED_DIR, f"predictions_{s}.csv"), index=False)

    # Save final live model state (ready for the live season).
    model.save(C.LIVE_STATE)

    # ---- 3. metrics ------------------------------------------------------
    done = preds[preds["completed"]].copy()
    _write_accuracy(done)
    _print_summary(done, model)
    return preds, model


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def _season_metrics(df):
    err = df["pred_spread"] - df["actual_spread"]
    home_win = df["actual_spread"] > 0
    pred_home_win = df["pred_spread"] > 0
    su_correct = (pred_home_win == home_win)
    p = df["win_prob_home"].clip(1e-6, 1 - 1e-6)
    y = home_win.astype(float)
    brier = float(np.mean((p - y) ** 2))
    logloss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return {
        "games": int(len(df)),
        "spread_MAE": float(err.abs().mean()),
        "spread_RMSE": float(np.sqrt((err ** 2).mean())),
        "SU_accuracy": float(su_correct.mean()),
        "brier": brier,
        "log_loss": logloss,
    }


def _write_accuracy(done):
    rows = []
    for s, grp in done.groupby("season"):
        m = _season_metrics(grp)
        m["season"] = int(s)
        rows.append(m)
    season_df = pd.DataFrame(rows)[
        ["season", "games", "spread_MAE", "spread_RMSE", "SU_accuracy", "brier", "log_loss"]
    ]
    season_df.to_csv(os.path.join(C.ACC_DIR, "season_accuracy.csv"), index=False)

    # Calibration bins (predicted home win prob vs realised frequency).
    bins = np.linspace(0, 1, 11)
    idx = np.clip(np.digitize(done["win_prob_home"], bins) - 1, 0, 9)
    cal_rows = []
    for b in range(10):
        sel = done[idx == b]
        if len(sel) == 0:
            continue
        cal_rows.append({
            "bin": f"{bins[b]:.1f}-{bins[b+1]:.1f}",
            "n": int(len(sel)),
            "pred_mean": float(sel["win_prob_home"].mean()),
            "actual_freq": float((sel["actual_spread"] > 0).mean()),
        })
    pd.DataFrame(cal_rows).to_csv(os.path.join(C.ACC_DIR, "calibration.csv"), index=False)


def _print_summary(done, model):
    overall = _season_metrics(done)
    overall["coefficients_standardized"] = model.coefficients()
    overall["residual_sigma_pts"] = float(np.sqrt(model.sigma2_hat))
    with open(os.path.join(C.ACC_DIR, "backtest_summary.json"), "w") as f:
        json.dump(overall, f, indent=2)
    print(f"\n=== OVERALL ({C.EVAL_SEASONS[0]}-{C.EVAL_SEASONS[-1]}, FBS vs FBS) ===")
    print(f"games        : {overall['games']}")
    print(f"spread MAE   : {overall['spread_MAE']:.2f} pts")
    print(f"spread RMSE  : {overall['spread_RMSE']:.2f} pts")
    print(f"SU accuracy  : {overall['SU_accuracy']*100:.1f}%")
    print(f"Brier score  : {overall['brier']:.4f}")
    print(f"Log loss     : {overall['log_loss']:.4f}")


if __name__ == "__main__":
    run_backtest()
