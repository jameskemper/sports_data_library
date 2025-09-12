#!/usr/bin/env python3
"""
schedule_scraper.py
Fetches the 2025 college football schedule from the CFBD API
and saves it as a CSV (no scores).
"""

import os
import requests
import pandas as pd

API_KEY = os.environ["CFBD_API_KEY"]
YEAR = 2025

BASE_URL = "https://api.collegefootballdata.com/games"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Ensure the data directory exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_schedule(year):
    url = f"{BASE_URL}?year={year}&seasonType=regular"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def compile_schedule(year):
    data = fetch_schedule(year)
    records = []

    for g in data:
        records.append({
            "season": g.get("season"),
            "week": g.get("week"),
            "season_type": g.get("seasonType"),
            "start_date": g.get("startDate"),
            "home_team": g.get("homeTeam"),
            "away_team": g.get("awayTeam"),
            "venue": g.get("venue"),
            "home_conference": g.get("homeConference"),
            "away_conference": g.get("awayConference"),
            "game_id": g.get("id")
        })

    return pd.DataFrame(records)

if __name__ == "__main__":
    df = compile_schedule(YEAR)
    outpath = os.path.join(DATA_DIR, f"schedule_{YEAR}.csv")
    df.to_csv(outpath, index=False)
    print(f"Saved schedule to {outpath}")
