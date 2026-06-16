"""
Predict a single WNBA game-day with the live Bayesian posterior.

Reads model_state/model_current.json and the season schedule, builds leakage-safe
pre-game features for every game on the target date, and writes:

    predictions/<season>/MM_DD_YYYY.csv

with the predicted winner, win probability, and point spread for each game.
The posterior is NOT modified here — learning happens in update_results.py once
the games are final.
"""

import os
import numpy as np
import pandas as pd

import config as C
import features as F
from model import BayesianSpreadModel

PRED_COLS = ["date", "season", "home_team", "away_team",
             "pred_spread", "win_prob_home", "win_prob_away",
             "predicted_winner", "winner_win_prob"]


def _day_filename(season, date):
    d = pd.Timestamp(date)
    return os.path.join(C.PRED_DIR, str(int(season)), d.strftime("%m_%d_%Y") + ".csv")


def next_slate_date(season, today=None):
    """First date in the schedule with games on/after `today` (default: now)."""
    sched = F._load_schedule(season)
    if sched.empty:
        return None
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    upcoming = sched[sched["Date"] >= today]
    if upcoming.empty:
        return None
    return upcoming["Date"].min()


def games_on(season, date):
    """List of (home, away) for `date` from the schedule (valid franchises only)."""
    sched = F._load_schedule(season)
    if sched.empty:
        return []
    d = pd.Timestamp(date)
    day = sched[sched["Date"] == d]
    return list(zip(day["HomeTeam"], day["AwayTeam"]))


def predict_day(season, date=None, model=None, write=True):
    F.clear_caches()
    if date is None:
        date = next_slate_date(season)
        if date is None:
            print(f"[predict] no upcoming games found for {season}.")
            return pd.DataFrame(columns=PRED_COLS)
    date = pd.Timestamp(date)

    games = games_on(season, date)
    if not games:
        print(f"[predict] no scheduled games on {date.date()}.")
        return pd.DataFrame(columns=PRED_COLS)

    if model is None:
        if not os.path.exists(C.LIVE_STATE):
            raise SystemExit("No live model — run `run_pipeline.py --mode backfill` first.")
        model = BayesianSpreadModel.load(C.LIVE_STATE)

    X, meta = F.build_day_matrix(season, date, games)
    out = model.predict(X)
    meta["pred_spread"] = np.round(out["pred_spread"], 2)
    meta["win_prob_home"] = np.round(out["win_prob_home"], 4)
    meta["win_prob_away"] = np.round(1.0 - out["win_prob_home"], 4)
    meta["predicted_winner"] = np.where(out["win_prob_home"] >= 0.5,
                                        meta["home_team"], meta["away_team"])
    meta["winner_win_prob"] = np.round(
        np.where(out["win_prob_home"] >= 0.5, out["win_prob_home"],
                 1.0 - out["win_prob_home"]), 4)
    meta = meta[PRED_COLS]

    if write:
        path = _day_filename(season, date)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        meta.to_csv(path, index=False)
        print(f"[predict] {len(meta)} games -> {os.path.relpath(path, C.HERE)}")
    return meta


if __name__ == "__main__":
    import argparse
    from run_pipeline import current_season
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--date", type=str, default=None, help="YYYY-MM-DD")
    args = ap.parse_args()
    predict_day(args.season or current_season(), args.date)
