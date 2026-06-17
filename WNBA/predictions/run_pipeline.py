"""
Orchestrator for the WNBA Bayesian prediction model — the single entry point the
scheduled GitHub Action calls.

Modes
-----
  --mode backfill : (one-off / rebuild) replay the full walk-forward history.
        Fits the standardiser on the burn-in season, then walks every later
        season one game-day at a time: predict the slate out-of-sample, write
        predictions/<season>/MM_DD_YYYY.csv, grade it, and assimilate the
        results into the posterior. Produces every historical daily file,
        model_state/model_after_<season>.json, model_current.json, the
        predictions_history ledger and the accuracy CSVs from scratch.

  --mode predict  : (daily, before games) load model_current.json and write the
        next slate's predictions. Does not change the posterior.

  --mode update   : (daily, after games) grade newly-final games, assimilate
        them into model_current.json, and refresh the accuracy CSVs.

The model consumes only the committed game-result/schedule CSVs that the WNBA
data workflow already produces, so this never scrapes anything itself.
"""

import os
import argparse
from datetime import date

import numpy as np
import pandas as pd

import config as C
import features as F
from model import BayesianSpreadModel
from predict_day import predict_day, next_slate_date, games_on
from update_results import update_results, _refresh_accuracy, HISTORY_COLS


def current_season(today=None):
    """WNBA season label = calendar year (May–October single-year season)."""
    return (today or date.today()).year


# --------------------------------------------------------------------------- #
# Backfill: rebuild the entire history with a clean walk-forward
# --------------------------------------------------------------------------- #
def backfill():
    F.clear_caches()
    print("=== backfill: walk-forward rebuild ===")

    Xb, yb, mb = F.build_dataset(C.BURN_IN_SEASONS)
    if len(Xb) == 0:
        raise SystemExit("No burn-in data found.")
    model = BayesianSpreadModel()
    model.fit_scaler(Xb)
    model.update(Xb, yb)
    last_burn = max(C.BURN_IN_SEASONS)
    model.save(os.path.join(C.STATE_DIR, f"model_after_{last_burn}.json"))
    print(f"burn-in {C.BURN_IN_SEASONS}: {len(Xb)} games -> scaler + posterior seeded.")

    history_rows = []
    for season in C.EVAL_SEASONS:
        results = F._load_results(season)
        if results.empty:
            continue
        model.discount(C.SEASON_DISCOUNT)
        n_season = 0
        for d, day in results.groupby("Date"):
            # 1) predict the day's scheduled slate out-of-sample, write daily file
            games = games_on(season, d) or list(zip(day["HomeTeam"], day["AwayTeam"]))
            predict_day(season, d, model=model, write=True)

            # 2) grade the completed games and assimilate them
            Xnew, ynew = [], []
            for _, gm in day.iterrows():
                x = F.build_feature_vector(season, d, gm["HomeTeam"], gm["AwayTeam"])
                o = model.predict_one(x)
                spread = float(gm["HomeScore"] - gm["AwayScore"])
                home_win = int(spread > 0)
                wph = round(o["win_prob_home"], 4)
                pred_home = wph >= 0.5
                history_rows.append({
                    "date": d.strftime("%Y-%m-%d"), "season": int(season),
                    "home_team": gm["HomeTeam"], "away_team": gm["AwayTeam"],
                    "home_score": float(gm["HomeScore"]), "away_score": float(gm["AwayScore"]),
                    "actual_spread": spread, "home_win": home_win,
                    "pred_spread": round(o["pred_spread"], 2), "win_prob_home": wph,
                    "predicted_winner": gm["HomeTeam"] if pred_home else gm["AwayTeam"],
                    "winner_win_prob": round(wph if pred_home else 1 - wph, 4),
                    "correct": int(pred_home == bool(home_win)),
                })
                Xnew.append(x)
                ynew.append(spread)
                n_season += 1
            if Xnew:
                model.update(np.vstack(Xnew), np.array(ynew))
        model.save(os.path.join(C.STATE_DIR, f"model_after_{season}.json"))
        acc = np.mean([r["correct"] for r in history_rows if r["season"] == season])
        print(f"season {season}: {n_season} games graded, accuracy {acc:.3f}")

    # write live model + ledger + accuracy
    model.save(C.LIVE_STATE)
    hist = pd.DataFrame(history_rows)[HISTORY_COLS]
    hist.to_csv(C.HISTORY_CSV, index=False)
    if os.path.exists(C.RUNNING_ACC_CSV):
        open(C.RUNNING_ACC_CSV, "w").close()  # truncate (remove blocked on OneDrive)
    hk = hist.copy()
    hk["key"] = hk["date"].astype(str) + "|" + hk["home_team"] + "|" + hk["away_team"]
    _refresh_accuracy(hk)
    print(f"\nbackfill complete: {len(hist)} games in ledger, "
          f"overall accuracy {hist['correct'].mean():.3f}")
    print(f"live model -> {os.path.relpath(C.LIVE_STATE, C.HERE)}")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["backfill", "predict", "update"], required=True)
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--date", type=str, default=None, help="YYYY-MM-DD (predict)")
    args = ap.parse_args()

    season = args.season or current_season()

    if args.mode == "backfill":
        backfill()
    elif args.mode == "update":
        update_results(season)
    else:  # predict
        if args.date is None and next_slate_date(season) is None:
            print(f"[predict] no upcoming games for {season} — nothing to do.")
            return
        predict_day(season, args.date)


if __name__ == "__main__":
    main()
