#!/usr/bin/env python3
"""
weekly_elo_scraper.py

Fetch weekly ELO ratings from the CollegeFootballData API
and save raw JSON to data/weeks_2025/week_##.json.
"""

import os
import json
import requests

# Config
API_KEY = os.environ["CFBD_API_KEY"]
YEAR = 2025
SEASON_TYPE = "regular"
LAST_WEEK = 20  # adjust if season has fewer/more weeks

# API base
BASE_URL = "https://api.collegefootballdata.com/ratings/elo"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_weekly_elo(year: int, week: int):
    """Fetch ELO ratings for a specific week."""
    url = f"{BASE_URL}?year={year}&week={week}&seasonType={SEASON_TYPE}"
    resp = requests.get(url, headers=HEADERS, timeout=30)

    if resp.status_code != 200:
        print(f"❌ Error {resp.status_code} fetching year {year} week {week}")
        return None

    try:
        return resp.json()
    except Exception:
        print(f"❌ Could not decode JSON for {year} week {week}")
        print("Response preview:", resp.text[:200])
        return None

def save_weekly_file(week: int, data: dict):
    """Save weekly data as JSON."""
    fname = os.path.join(DATA_DIR, f"week_{week:02d}.json")
    with open(fname, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {fname}")

def main():
    for week in range(1, LAST_WEEK + 1):
        print(f"📅 Fetching {YEAR} Week {week} ELO ratings...")
        data = fetch_weekly_elo(YEAR, week)
        if data:
            save_weekly_file(week, data)

if __name__ == "__main__":
    main()
