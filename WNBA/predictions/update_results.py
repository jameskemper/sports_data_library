"""
Grade finished games, teach the posterior, and refresh accuracy files.

For every completed game (in game_results_<season>.csv) that has a stored daily
prediction but has not yet been graded, this:
    1. joins the stored prediction to the realised result,
    2. appends a row to accuracy/predictions_history.csv,
    3. assimilates the game into the live posterior (online Bayesian update),
    4. rewrites accuracy/season_accuracy.csv (running, per season),
    5. appends a snapshot to accuracy/running_accuracy.csv (cumulative).

predictions_history.csv is the ledger of what has been learned: a game is
assimilated exactly once, the first time it is graded. This keeps the live model
and the accuracy stats perfectly in sync.
"""

import os
import numpy as np
import pandas as pd

import config as C
import features as F
from model import BayesianSpreadModel

HISTORY_COLS = ["date", "season", "home_team", "away_team",
                "home_score", "away_score", "actual_spread", "home_win",
                "pred_spread", "win_prob_home", "predicted_winner",
                "winner_win_prob", "correct"]


def _load_history():
    if os.path.exists(C.HISTORY_CSV):
        h = pd.read_csv(C.HISTORY_CSV)
        h["key"] = h["date"].astype(str) + "|" + h["home_team"] + "|" + h["away_team"]
        return h
    return pd.DataFrame(columns=HISTORY_COLS + ["key"])


def _load_day_predictions(season, date):
    from predict_day import _day_filename
    path = _day_filename(season, date)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def _refresh_accuracy(history):
    """Rewrite season_accuracy.csv and append to running_accuracy.csv."""
    h = history.drop(columns=["key"], errors="ignore").copy()
    if h.empty:
        return
    h = h.sort_values("date")

    def agg(df):
        p = df["win_prob_home"].to_numpy()
        y = df["home_win"].to_numpy()
        return pd.Series({
            "games": len(df),
            "correct": int(df["correct"].sum()),
            "accuracy": round(float(df["correct"].mean()), 4),
            "brier": round(float(np.mean((p - y) ** 2)), 4),
            "spread_mae": round(float(np.mean(np.abs(df["pred_spread"] - df["actual_spread"]))), 2),
        })

    season_tbl = h.groupby("season").apply(agg, include_groups=False).reset_index()
    season_tbl.to_csv(C.SEASON_ACC_CSV, index=False)

    # cumulative running snapshot (one row per run that grades >=1 game)
    overall = agg(h)
    snap = pd.DataFrame([{
        "run_date": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "through_date": h["date"].max(),
        "total_games": int(overall["games"]),
        "total_correct": int(overall["correct"]),
        "cumulative_accuracy": overall["accuracy"],
        "cumulative_brier": overall["brier"],
        "cumulative_spread_mae": overall["spread_mae"],
    }])
    if os.path.exists(C.RUNNING_ACC_CSV):
        prev = pd.read_csv(C.RUNNING_ACC_CSV)
        snap = pd.concat([prev, snap], ignore_index=True)
    snap.to_csv(C.RUNNING_ACC_CSV, index=False)


def update_results(season, model=None, save_model=True):
    """Grade + learn from all newly-final games of `season`. Returns #graded."""
    F.clear_caches()
    results = F._load_results(season)
    if results.empty:
        print(f"[update] no completed games for {season}.")
        return 0

    history = _load_history()
    seen = set(history["key"]) if not history.empty else set()

    if model is None:
        if not os.path.exists(C.LIVE_STATE):
            raise SystemExit("No live model — run `run_pipeline.py --mode backfill` first.")
        model = BayesianSpreadModel.load(C.LIVE_STATE)

    new_rows, Xnew, ynew = [], [], []
    for date, day in results.groupby("Date"):
        preds = _load_day_predictions(season, date)
        for _, gm in day.iterrows():
            key = f"{date.strftime('%Y-%m-%d')}|{gm['HomeTeam']}|{gm['AwayTeam']}"
            if key in seen:
                continue
            spread = float(gm["HomeScore"] - gm["AwayScore"])
            home_win = int(spread > 0)

            # stored pre-game prediction (fall back to a fresh leakage-safe one
            # if no daily file exists — same features, current posterior)
            pr = None
            if preds is not None:
                match = preds[(preds["home_team"] == gm["HomeTeam"]) &
                              (preds["away_team"] == gm["AwayTeam"])]
                if len(match):
                    pr = match.iloc[0]
            if pr is None:
                x = F.build_feature_vector(season, date, gm["HomeTeam"], gm["AwayTeam"])
                o = model.predict_one(x)
                pred_spread = round(o["pred_spread"], 2)
                wph = round(o["win_prob_home"], 4)
                winner = gm["HomeTeam"] if wph >= 0.5 else gm["AwayTeam"]
                wwp = round(wph if wph >= 0.5 else 1 - wph, 4)
            else:
                pred_spread = float(pr["pred_spread"])
                wph = float(pr["win_prob_home"])
                winner = pr["predicted_winner"]
                wwp = float(pr["winner_win_prob"])

            pred_home = wph >= 0.5
            correct = int(pred_home == bool(home_win))
            new_rows.append({
                "date": date.strftime("%Y-%m-%d"), "season": int(season),
                "home_team": gm["HomeTeam"], "away_team": gm["AwayTeam"],
                "home_score": float(gm["HomeScore"]), "away_score": float(gm["AwayScore"]),
                "actual_spread": spread, "home_win": home_win,
                "pred_spread": pred_spread, "win_prob_home": wph,
                "predicted_winner": winner, "winner_win_prob": wwp,
                "correct": correct,
            })
            Xnew.append(F.build_feature_vector(season, date, gm["HomeTeam"], gm["AwayTeam"]))
            ynew.append(spread)
            seen.add(key)

    if not new_rows:
        print(f"[update] nothing new to grade for {season}.")
        return 0

    # 1) assimilate (online Bayesian learning)
    model.update(np.vstack(Xnew), np.array(ynew))
    if save_model:
        model.save(C.LIVE_STATE)

    # 2) append to history ledger
    add = pd.DataFrame(new_rows)
    if os.path.exists(C.HISTORY_CSV):
        full = pd.concat([pd.read_csv(C.HISTORY_CSV), add], ignore_index=True)
    else:
        full = add
    full = full[HISTORY_COLS]
    full.to_csv(C.HISTORY_CSV, index=False)

    # 3) refresh accuracy summaries
    full_keyed = full.copy()
    full_keyed["key"] = (full_keyed["date"].astype(str) + "|" +
                         full_keyed["home_team"] + "|" + full_keyed["away_team"])
    _refresh_accuracy(full_keyed)

    print(f"[update] graded {len(add)} new games for {season} "
          f"(season accuracy now {add['correct'].mean():.3f} on this batch).")
    return len(add)


if __name__ == "__main__":
    import argparse
    from run_pipeline import current_season
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None)
    args = ap.parse_args()
    update_results(args.season or current_season())
