#!/usr/bin/env python3
"""
weekly_elo_scraper.py

Fetches weekly ELO ratings from the CFBD API and saves them as CSVs.
"""

import os
import time
import requests
import pandas as pd

YEAR = 2025
SEASON_TYPE = "regular"
LAST_WEEK = 20
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"weeks_{YEAR}")
os.makedirs(SAVE_DIR, exist_ok=True)

API_KEY = os.getenv("CFBD_API_KEY")
if not API_KEY:
    raise RuntimeError("CFBD_API_KEY is not set in environment variables")

BASE_URL = "https://api.collegefootballdata.com/elo"

headers = {"Authorization": f"Bearer {API_KEY}"}

def fetch_weekly_elo(year, week):
    url = f"{BASE_URL}?year={year}&week={week}&seasonType={SEASON_TYPE}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Error fetching year {year} week {week}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    if not data:
        print(f"⚠️ No data for {year} week {week}")
        return None
    return pd.DataFrame(data)

def main():
    for week in range(1, LAST_WEEK + 1):
        print(f"📅 Fetching {YEAR} Week {week} ELO ratings...")
        df = fetch_weekly_elo(YEAR, week)
        if df is not None:
            out_path = os.path.join(SAVE_DIR, f"week_{week:02d}.csv")
            df.to_csv(out_path, index=False)
            print(f"✅ Saved {out_path}")
        time.sleep(1)

if __name__ == "__main__":
    main()
