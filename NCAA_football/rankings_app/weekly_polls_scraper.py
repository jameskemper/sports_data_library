#!/usr/bin/env python3
"""
weekly_polls_scraper.py

Fetches CFBD weekly poll data (weeks 1–16) and saves JSON
to data/weeks_<YEAR>/week_##.json ONLY if data changed.
"""

import os
import json
import requests
import hashlib

API_KEY     = os.environ["CFBD_API_KEY"]
YEAR        = int(os.getenv("YEAR", 2025))
SEASON_TYPE = "regular"
LAST_WEEK   = 16

# Directories
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
os.makedirs(WEEKS_DIR, exist_ok=True)

def fetch_week_data(week):
    url = f"https://api.collegefootballdata.com/rankings?year={YEAR}&week={week}&seasonType={SEASON_TYPE}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def save_if_changed(week, data):
    """Save week JSON only if it's new/different."""
    filename = os.path.join(WEEKS_DIR, f"week_{week:02}.json")
    new_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    if os.path.exists(filename):
        with open(filename, "r") as f:
            old_data = json.load(f)
        old_hash = hashlib.md5(json.dumps(old_data, sort_keys=True).encode()).hexdigest()
        if old_hash == new_hash:
            print(f"Week {week}: No change, skipping save.")
            return False

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Week {week}: New data saved.")
    return True

def main():
    changed = False
    for week in range(1, LAST_WEEK + 1):
        try:
            data = fetch_week_data(week)
            if not data:
                print(f"Week {week}: No data returned, skipping.")
                continue
            if save_if_changed(week, data):
                changed = True
        except Exception as e:
            print(f"Week {week}: Error fetching data → {e}")

    if changed:
        with open(os.path.join(BASE_DIR, "polls_changed.flag"), "w") as f:
            f.write("true")

if __name__ == "__main__":
    main()
