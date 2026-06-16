"""
Walk-forward backtest for the WNBA Bayesian spread model.

Protocol (no look-ahead at any step)
------------------------------------
  1. Fit the feature standardiser on the burn-in season(s) only.
  2. Initialise the posterior and assimilate every burn-in game.
  3. For each evaluation season, in chronological order:
       - apply the season forgetting factor,
       - process the season one GAME-DAY at a time:
           * predict every game scheduled that day using the CURRENT posterior
             (i.e. strictly out-of-sample — that day's results are not yet seen),
           * score those predictions,
           * THEN update the posterior with the day's realised results.

This mirrors production exactly: predict the slate in the morning, grade and
learn after the games finish.

Run:  python backtest.py
Writes accuracy/backtest_summary.json and prints a report.
"""

import json
import numpy as np
import pandas as pd

import config as C
import features as F
from model import BayesianSpreadModel


def _metrics(df):
    """df needs columns: home_win, win_prob_home, pred_spread, actual_spread."""
    p = df["win_prob_home"].to_numpy()
    y = df["home_win"].to_numpy()
    pred_home = (p >= 0.5).astype(int)
    eps = 1e-12
    return {
        "n": int(len(df)),
        "accuracy": float((pred_home == y).mean()),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))),
        "spread_mae": float(np.mean(np.abs(df["pred_spread"] - df["actual_spread"]))),
        "spread_rmse": float(np.sqrt(np.mean((df["pred_spread"] - df["actual_spread"]) ** 2))),
    }


def _calibration(df, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    p = df["win_prob_home"].to_numpy()
    y = df["home_win"].to_numpy()
    rows = []
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        rows.append({"bin_lo": round(float(edges[b]), 2),
                     "bin_hi": round(float(edges[b + 1]), 2),
                     "n": int(m.sum()),
                     "pred_mean": round(float(p[m].mean()), 4),
                     "actual_rate": round(float(y[m].mean()), 4)})
    return rows


def run_backtest(verbose=True):
    F.clear_caches()

    # --- burn-in: scaler + initial posterior -----------------------------
    Xb, yb, mb = F.build_dataset(C.BURN_IN_SEASONS)
    if len(Xb) == 0:
        raise SystemExit("No burn-in data found.")
    model = BayesianSpreadModel()
    model.fit_scaler(Xb)
    model.update(Xb, yb)
    if verbose:
        print(f"Burn-in seasons {C.BURN_IN_SEASONS}: {len(Xb)} games assimilated.")

    # --- walk forward over evaluation seasons ----------------------------
    graded = []
    for season in C.EVAL_SEASONS:
        Xs, ys, ms = F.build_dataset([season])
        if len(Xs) == 0:
            continue
        model.discount(C.SEASON_DISCOUNT)

        ms = ms.reset_index(drop=True)
        for date, day_idx in ms.groupby("date").groups.items():
            day_idx = list(day_idx)
            Xd = Xs[day_idx]
            out = model.predict(Xd)
            rec = ms.loc[day_idx].copy()
            rec["pred_spread"] = out["pred_spread"]
            rec["win_prob_home"] = out["win_prob_home"]
            graded.append(rec)
            # learn from the day's results
            model.update(Xd, ys[day_idx])

        if verbose:
            sub = pd.concat(graded)
            sub = sub[sub["season"] == season]
            print(f"  {season}: {_metrics(sub)}")

    allg = pd.concat(graded, ignore_index=True)

    # --- baselines for context -------------------------------------------
    home_always = float((allg["home_win"] == 1).mean())  # accuracy of "home wins"
    # "stronger season-to-date net rating wins" baseline
    net_pick = (allg["pred_spread"] * 0 + (allg["actual_spread"]))  # placeholder, unused

    summary = {
        "burn_in_seasons": C.BURN_IN_SEASONS,
        "eval_seasons": C.EVAL_SEASONS,
        "season_discount": C.SEASON_DISCOUNT,
        "overall": _metrics(allg),
        "by_season": {int(s): _metrics(allg[allg["season"] == s])
                      for s in sorted(allg["season"].unique())},
        "baseline_home_team_accuracy": round(home_always, 4),
        "calibration": _calibration(allg),
        "coefficients_final": model.coefficients(),
    }

    with open(C.BACKTEST_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        o = summary["overall"]
        print("\n=== WNBA Bayesian model — walk-forward backtest ===")
        print(f"Eval games:      {o['n']}")
        print(f"Winner accuracy: {o['accuracy']:.3f}   (home-always baseline {home_always:.3f})")
        print(f"Brier score:     {o['brier']:.4f}   (0.25 = coin flip)")
        print(f"Log loss:        {o['log_loss']:.4f}")
        print(f"Spread MAE:      {o['spread_mae']:.2f} pts")
        print(f"Spread RMSE:     {o['spread_rmse']:.2f} pts")
        print(f"Saved -> {C.BACKTEST_JSON}")
    return summary


if __name__ == "__main__":
    run_backtest()
