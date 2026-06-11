"""
Generate predictions for an upcoming week from the CURRENT saved model state.

This is the "live" predictor. It does NOT peek at results — it loads the
posterior saved in model_state/model_current.json (produced by the backtest, or
rolled forward in-season by update_results.py) and scores every FBS-vs-FBS game
scheduled for the requested (season, week).

Usage:
    python predict_week.py --season 2026 --week 1
    python predict_week.py                      # auto: latest season, next unplayed week

Output:
    predictions/predictions/predictions_{season}.csv   (appended / upserted)
    Also prints a readable table.
"""

import os
import argparse
import numpy as np
import pandas as pd

import features as F
from model import BayesianSpreadModel
import config as C


def _latest_season():
    seasons = []
    for fn in os.listdir(F.BOX_SCORES):
        if fn.startswith("box_scores_") and fn.endswith(".csv"):
            try:
                seasons.append(int(fn.split("_")[-1].split(".")[0]))
            except ValueError:
                pass
    return max(seasons) if seasons else None


def _next_unplayed_week(season):
    df = F._load_box_scores(season)
    if df.empty:
        return 1
    if "completed" in df.columns:
        pending = df[~df["completed"].astype(bool)]
        if not pending.empty:
            return int(pending["week"].min())
    return int(df["week"].max())


def predict_week(season, week, state_path=None, save=True, fbs_only=True):
    state_path = state_path or C.LIVE_STATE
    if not os.path.exists(state_path):
        raise FileNotFoundError(
            f"No model state at {state_path}. Run backtest.py first to initialise it.")
    model = BayesianSpreadModel.load(state_path)

    X, meta = F.build_week_matrix(season, week, fbs_only=fbs_only)
    if len(meta) == 0:
        print(f"No FBS-vs-FBS games found for {season} week {week}.")
        return pd.DataFrame()

    out = model.predict(X)
    meta = meta.copy()
    meta["pred_spread"] = np.round(out["pred_spread"], 2)
    meta["win_prob_home"] = np.round(out["win_prob_home"], 4)
    meta["pp_scale"] = np.round(out["pp_scale"], 2)
    meta["pred_winner"] = np.where(meta["pred_spread"] >= 0, meta["home_team"], meta["away_team"])
    meta["pred_win_prob"] = np.round(
        np.where(meta["pred_spread"] >= 0, out["win_prob_home"], 1 - out["win_prob_home"]), 4)
    meta["model_n_obs"] = model.n_obs
    meta["predicted_at_state"] = os.path.basename(state_path)

    if save:
        _upsert(season, meta)

    # readable summary
    show = meta[["week", "home_team", "away_team", "pred_spread",
                 "pred_winner", "pred_win_prob"]].copy()
    show["line"] = show.apply(
        lambda r: f"{r.home_team} {'-' if r.pred_spread>=0 else '+'}{abs(r.pred_spread):.1f}", axis=1)
    print(f"\n{season} Week {week} — {len(meta)} games "
          f"(model trained on {model.n_obs} games)\n")
    for _, r in show.iterrows():
        print(f"  {r.home_team:>22} vs {r.away_team:<22}  "
              f"{r.line:>14}   {r.pred_winner} {r.pred_win_prob*100:4.1f}%")
    return meta


def _upsert(season, new_rows):
    """Write/merge predictions into predictions_{season}.csv keyed by game_id."""
    path = os.path.join(C.PRED_DIR, f"predictions_{season}.csv")
    if os.path.exists(path):
        old = pd.read_csv(path)
        old = old[~old["game_id"].isin(new_rows["game_id"])]
        combined = pd.concat([old, new_rows], ignore_index=True)
    else:
        combined = new_rows
    combined = combined.sort_values(["week", "home_team"]).reset_index(drop=True)
    combined.to_csv(path, index=False)
    print(f"Saved -> {path} ({len(combined)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--state", type=str, default=None, help="path to model state json")
    args = ap.parse_args()

    season = args.season or _latest_season()
    week = args.week or _next_unplayed_week(season)
    predict_week(season, week, state_path=args.state)
