"""
Roll the model forward after a week's games finish.

This is the Bayesian learning step for live use: it takes the completed games
for (season, week), updates the posterior (current posterior -> prior for next
week), saves the new model_current.json, and refreshes season accuracy by
scoring the predictions that were made BEFORE these games (stored earlier by
predict_week.py).

Order of operations in a normal week:
    1. predict_week.py  --season S --week W   (before games)
    2. ... games are played, box scores update ...
    3. update_results.py --season S --week W  (after games)

Usage:
    python update_results.py --season 2026 --week 1
    python update_results.py                      # auto: latest completed week

Outputs:
    model_state/model_current.json        updated posterior
    model_state/model_after_{S}wk{W}.json snapshot
    accuracy/season_accuracy_live.csv     running accuracy for the live season
"""

import os
import argparse
import numpy as np
import pandas as pd

import features as F
from model import BayesianSpreadModel
import config as C


def _latest_completed_week(season):
    df = F._load_box_scores(season)
    if df.empty or "completed" not in df.columns:
        return None
    done = df[df["completed"].astype(bool)]
    return int(done["week"].max()) if not done.empty else None


def update_results(season, week, state_path=None, fbs_only=True):
    state_path = state_path or C.LIVE_STATE
    if not os.path.exists(state_path):
        raise FileNotFoundError(f"No model state at {state_path}. Run backtest.py first.")
    model = BayesianSpreadModel.load(state_path)

    X, meta = F.build_week_matrix(season, week, fbs_only=fbs_only)
    if len(meta) == 0:
        print(f"No games for {season} week {week}.")
        return
    mask = meta["completed"].values
    n_done = int(mask.sum())
    if n_done == 0:
        print(f"{season} week {week}: no completed games yet — nothing to update.")
        return

    before = model.n_obs
    model.update(X[mask], meta.loc[mask, "actual_spread"].values)
    model.save(state_path)
    model.save(os.path.join(C.STATE_DIR, f"model_after_{season}wk{week:02d}.json"))
    print(f"Posterior updated with {n_done} games "
          f"({before} -> {model.n_obs}); sigma~{np.sqrt(model.sigma2_hat):.1f} pts")

    _refresh_accuracy(season)


def _refresh_accuracy(season):
    """Score all saved predictions for the season against actual results."""
    path = os.path.join(C.PRED_DIR, f"predictions_{season}.csv")
    if not os.path.exists(path):
        return
    preds = pd.read_csv(path)

    # Attach actual results from box scores.
    box = F._load_box_scores(season)
    if box.empty:
        return
    box = box[["id", "completed", "home_points", "away_points"]].rename(columns={"id": "game_id"})
    df = preds.merge(box, on="game_id", how="left", suffixes=("", "_actual"))
    hp = df.get("home_points_actual", df.get("home_points"))
    ap = df.get("away_points_actual", df.get("away_points"))
    df["actual_spread"] = hp - ap
    done = df[df["completed_actual"].fillna(False).astype(bool) & df["actual_spread"].notna()].copy()
    if done.empty:
        print("No completed predicted games to score yet.")
        return

    err = done["pred_spread"] - done["actual_spread"]
    home_win = done["actual_spread"] > 0
    su = (done["pred_spread"] > 0) == home_win
    p = done["win_prob_home"].clip(1e-6, 1 - 1e-6)
    y = home_win.astype(float)
    row = {
        "season": season,
        "games_scored": int(len(done)),
        "spread_MAE": round(float(err.abs().mean()), 3),
        "spread_RMSE": round(float(np.sqrt((err ** 2).mean())), 3),
        "SU_accuracy": round(float(su.mean()), 4),
        "brier": round(float(np.mean((p - y) ** 2)), 4),
        "log_loss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4),
    }
    out = os.path.join(C.ACC_DIR, "season_accuracy_live.csv")
    if os.path.exists(out):
        acc = pd.read_csv(out)
        acc = acc[acc["season"] != season]
        acc = pd.concat([acc, pd.DataFrame([row])], ignore_index=True)
    else:
        acc = pd.DataFrame([row])
    acc.sort_values("season").to_csv(out, index=False)
    print(f"Season {season} accuracy: SU {row['SU_accuracy']*100:.1f}%, "
          f"spread MAE {row['spread_MAE']} pts ({row['games_scored']} games) -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--state", type=str, default=None)
    args = ap.parse_args()

    season = args.season
    if season is None:
        seasons = [int(fn.split("_")[-1].split(".")[0])
                   for fn in os.listdir(F.BOX_SCORES)
                   if fn.startswith("box_scores_") and fn.endswith(".csv")]
        season = max(seasons)
    week = args.week or _latest_completed_week(season)
    if week is None:
        print("No completed week found.")
    else:
        update_results(season, week, state_path=args.state)
