#!/usr/bin/env python3
import os
import requests
import pandas as pd

API_KEY = os.environ["CFBD_API_KEY"]
YEAR = 2025
SEASON_TYPE = "regular"
LAST_WEEK = 20

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
os.makedirs(WEEKS_DIR, exist_ok=True)

def fetch_weekly_elo(year, week):
    url = f"https://api.collegefootballdata.com/ratings/elo?year={year}&week={week}&seasonType={SEASON_TYPE}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Error fetching {year} week {week}: {resp.text[:200]}")
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
        if df is not None and not df.empty:
            out_path = os.path.join(WEEKS_DIR, f"week_{week:02d}.csv")
            df.to_csv(out_path, index=False)
            print(f"✅ Saved {out_path}")
        else:
            print(f"⚠️ No data saved for Week {week}")

if __name__ == "__main__":
    main()
