#!/usr/bin/env python3
"""
weekly_polls_scraper.py

Fetches CFBD weekly poll data for one week (auto-increment or specified),
and saves raw JSON to data/weeks_<YEAR>/week_##.json.
"""

import os
import json
import requests

API_KEY     = os.environ["CFBD_API_KEY"]
YEAR        = 2025
SEASON_TYPE = "regular"
WEEK        = None
LAST_WEEK   = 16

# Use script location for all relative paths
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")

os.makedirs(WEEKS_DIR, exist_ok=True)

def existing_weeks():
    files = os.listdir(WEEKS_DIR)
    weeks = [
        int(f.split("_")[1].split(".")[0])
        for f in files if f.startswith("week_") and f.endswith(".json")
    ]
    return sorted(weeks)

def next_week():
    seen = set(existing_weeks())
    for w in range(1, LAST_WEEK + 1):
        if w not in seen:
            return w
    return None

def fetch_week_json(week: int):
    url = "https://apinext.collegefootballdata.com/rankings"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    params = {"year": YEAR, "seasonType": SEASON_TYPE, "week": week}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()

def main():
    wk = WEEK or next_week()
    if wk is None:
        print("All weeks fetched.")
        return

    print(f"Fetching week {wk}...")
    data = fetch_week_json(wk)
    path = os.path.join(WEEKS_DIR, f"week_{wk:02d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved raw JSON to {path}")

if __name__ == "__main__":
    main()
