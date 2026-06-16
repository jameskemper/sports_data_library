"""Shared configuration and paths for the WNBA prediction pipeline.

Folder layout (everything lives under WNBA/predictions/):
    predictions/<season>/MM_DD_YYYY.csv   one file per game-day, daily predictions
    accuracy/predictions_history.csv      one row per graded game (pred vs actual)
    accuracy/season_accuracy.csv          running accuracy per season
    accuracy/running_accuracy.csv         appended log of cumulative accuracy by run
    accuracy/backtest_summary.json        walk-forward backtest metrics
    model_state/model_after_<season>.json posterior snapshot after each season
    model_state/model_current.json        the live posterior used for prediction
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PRED_DIR = os.path.join(HERE, "predictions")     # per-day prediction CSVs (in season subfolders)
ACC_DIR = os.path.join(HERE, "accuracy")          # accuracy / calibration / backtest
STATE_DIR = os.path.join(HERE, "model_state")     # saved posterior snapshots

for _d in (PRED_DIR, ACC_DIR, STATE_DIR):
    os.makedirs(_d, exist_ok=True)

LIVE_STATE = os.path.join(STATE_DIR, "model_current.json")
HISTORY_CSV = os.path.join(ACC_DIR, "predictions_history.csv")
SEASON_ACC_CSV = os.path.join(ACC_DIR, "season_accuracy.csv")
RUNNING_ACC_CSV = os.path.join(ACC_DIR, "running_accuracy.csv")
BACKTEST_JSON = os.path.join(ACC_DIR, "backtest_summary.json")

# --- data location --------------------------------------------------------
BASE = os.path.join(HERE, "..")
GAME_RESULTS_DIR = os.path.join(BASE, "game_results_app", "data")

# --- walk-forward configuration ------------------------------------------
# 2024 is the earliest full season in the library -> burn-in (initialise the
# posterior + standardisation). 2025 onward are genuine out-of-sample seasons.
# NOTE: append the new year to EVAL_SEASONS before each season so the model
# assimilates the just-finished season into model_current.json.
BURN_IN_SEASONS = [2024]
EVAL_SEASONS = [2025, 2026]

# --- forgetting factor ----------------------------------------------------
# Applied at the start of each new season: re-inflates uncertainty so the model
# adapts to roster turnover / expansion teams without discarding what it learned.
# 1.0 = no forgetting.
SEASON_DISCOUNT = 0.80

# --- valid franchises (excludes All-Star / national-team exhibitions) ------
VALID_TEAMS = {
    "Aces", "Dream", "Fever", "Fire", "Liberty", "Lynx", "Mercury",
    "Mystics", "Sky", "Sparks", "Storm", "Sun", "Tempo", "Valkyries", "Wings",
}
