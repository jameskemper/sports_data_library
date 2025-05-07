#!/usr/bin/env python3
"""
weekly_team_stats_scraper.py

Fetches CFBD advanced team stats for one week (auto-increment or specified),
and saves a per-week CSV to:
  shiny_app/team_stats_app/data/weeks_<YEAR>/advanced_stats_week_<WW>.csv
"""

import os
import requests
import pandas as pd

# Load API key from environment (set via CFBD_API_KEY)
API_KEY = os.environ["CFBD_API_KEY"]

# Configuration
YEAR        = 2025       # practicing with 2025 data
SEASON_TYPE = "regular"
CLASSIF     = "fbs"
WEEK        = None       # if None, auto-picks next missing week
LAST_WEEK   = 16         # adjust if needed

# Base paths
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(BASE_DIR, "data")
WEEKS_DIR = os.path.join(DATA_ROOT, f"weeks_{YEAR}")

os.makedirs(WEEKS_DIR, exist_ok=True)

# Team name corrections (extend if you spot others)
TEAM_CORR = {
    "San JosÃ© State": "San Jose State",
    "San Jos\303\251 State": "San Jose State",
    "San José State": "San Jose State",
}

def existing_weeks():
    """Return sorted list of already-fetched week numbers."""
    files = [f for f in os.listdir(WEEKS_DIR) if f.startswith("advanced_stats_week_") and f.endswith(".csv")]
    weeks = [int(f.split("_")[-1].split(".")[0]) for f in files]
    return sorted(weeks)

def next_week():
    """Choose the next missing week, or None if all done."""
    seen = set(existing_weeks())
    for w in range(1, LAST_WEEK + 1):
        if w not in seen:
            return w
    return None

def fetch_week(week: int) -> pd.DataFrame:
    """Fetch advanced stats for a single week and return a cleaned DataFrame."""
    url = "https://api.collegefootballdata.com/stats/season/advanced"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {
        "year": YEAR,
        "seasonType": SEASON_TYPE,
        "classification": CLASSIF,
        "excludeGarbageTime": True,
        "startWeek": week,
        "endWeek": week
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    df = pd.json_normalize(r.json())
    return df.replace(TEAM_CORR)

def main():
    wk = WEEK or next_week()
    if wk is None:
        print("All weeks fetched.")
        return

    print(f"Fetching advanced stats for week {wk}…")
    df = fetch_week(wk)
    out_path = os.path.join(WEEKS_DIR, f"advanced_stats_week_{wk:02d}.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()
