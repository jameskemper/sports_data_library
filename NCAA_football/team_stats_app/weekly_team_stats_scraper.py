#!/usr/bin/env python3
"""
weekly_team_stats_scraper.py

Fetches advanced team stats from the CFBD API for all weeks played
up to the current week of the season. Cleans the nested offense/defense
stats into flat columns and saves each week into:
data/weeks_<YEAR>/advanced_stats_week_##.csv
"""

import os
import requests
import pandas as pd
from datetime import datetime

# Config
API_KEY = os.environ["CFBD_API_KEY"]
YEAR = int(os.environ.get("YEAR", "2025"))
SEASON_TYPE = "regular"

# API base
BASE_URL = "https://api.collegefootballdata.com/stats/season/advanced"
HEADERS = {"Authorization": f"Bearer " + API_KEY}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_week_stats(year: int, week: int):
    """Fetch and flatten advanced team stats for a specific week."""
    url = f"{BASE_URL}?year={year}&week={week}&seasonType={SEASON_TYPE}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        print(f"No data returned for week {week}")
        return None

    flat_rows = []
    for row in data:
        base = {k: v for k, v in row.items() if k not in ["offense", "defense"]}
        offense = row.get("offense", {}) or {}
        defense = row.get("defense", {}) or {}
        flat_row = {
            **base,
            **{f"off_{k}": v for k, v in offense.items()},
            **{f"def_{k}": v for k, v in defense.items()},
        }
        flat_rows.append(flat_row)

    return pd.DataFrame(flat_rows)


def get_current_week(year: int):
    """Find the current week number from the CFBD API calendar."""
    url = f"https://api.collegefootballdata.com/calendar?year={year}&seasonType={SEASON_TYPE}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    calendar = resp.json()

    today = datetime.utcnow().date()
    played_weeks = [
        c["week"]
        for c in calendar
        if "startDate" in c and datetime.fromisoformat(c["startDate"][:-1]).date() <= today
    ]
    return max(played_weeks) if played_weeks else 1


def main():
    current_week = get_current_week(YEAR)
    print(f"Fetching advanced stats for weeks 1 through {current_week}…")

    for week in range(1, current_week + 1):
        out_path = os.path.join(DATA_DIR, f"advanced_stats_week_{week:02d}.csv")
        if os.path.exists(out_path):
            print(f"Week {week} already exists, skipping.")
            continue

        df = fetch_week_stats(YEAR, week)
        if df is not None:
            df.to_csv(out_path, index=False)
            print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
