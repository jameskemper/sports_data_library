"""Shared configuration and paths for the prediction pipeline."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PRED_DIR = os.path.join(HERE, "predictions")     # per-game prediction CSVs
ACC_DIR = os.path.join(HERE, "accuracy")          # season accuracy/calibration
STATE_DIR = os.path.join(HERE, "model_state")     # saved posterior snapshots

for _d in (PRED_DIR, ACC_DIR, STATE_DIR):
    os.makedirs(_d, exist_ok=True)

LIVE_STATE = os.path.join(STATE_DIR, "model_current.json")

# --- walk-forward configuration ------------------------------------------
BURN_IN_SEASONS = list(range(2010, 2015))   # 2010-2014: initialise posterior + scaler
EVAL_SEASONS = list(range(2015, 2026))      # 2015-2025: genuine pre-game predictions
# NOTE: bump the upper bound each year (e.g. 2027) before the new season so the
# model assimilates the just-finished season into model_current.json.

# --- forgetting factors ---------------------------------------------------
# Applied at the start of each new season (re-inflates uncertainty so the
# model adapts to roster/coaching turnover). 1.0 = no forgetting.
SEASON_DISCOUNT = 0.80
# Optional mild weekly forgetting (1.0 = off).
WEEKLY_DISCOUNT = 1.0

FBS_ONLY = True
