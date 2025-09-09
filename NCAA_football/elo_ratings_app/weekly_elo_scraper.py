#!/usr/bin/env python3
"""
weekly_elo_scraper.py

Fetches weekly ELO ratings from the CFBD API and saves them as CSVs.
"""

import os
import time
import pandas as pd
import cfbd
from cfbd.api import EloApi
from cfbd.rest import ApiException
from cfbd.configuration import Configuration

# --- CONFIG ---
YEAR = 2025
LAST_WEEK = 20
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"weeks_{YEAR}")
os.makedirs(SAVE_DIR, exist_ok=True)

# --- AUTHENTICATION ---
configuration = Configuration()
configuration.api_key["Authorization"] = os.getenv("CFBD_API_KEY")
configuration.api_key_prefix["Authorization"] = "Bearer"
api_client = cfbd.ApiClient(configuration)
elo_api = EloApi(api_client)

def fetch_weekly_elo(year, week):
    """Fetch ELO ratings for a given year and week."""
    try:
        ratings = elo_api.get_elo_ratings(year=year, week=week, season_type="regular")
        if not ratings:
            print(f"⚠️ No ELO data for {year} week {week}")
            return None

        rows = []
        for r in ratings:
            rows.append({
                "season": r.season,
                "week": r.week,
                "season_type": r.season_type,
                "team": r.team,
                "elo": r.elo,
                "elo_prob": r.elo_prob
            })
        return pd.DataFrame(rows)

    except ApiException as e:
        print(f"❌ API error fetching {year} week {week}: {e}")
        return None

def main():
    for week in range(1, LAST_WEEK + 1):
        print(f"📅 Fetching {YEAR} Week {week} ELO ratings...")
        df = fetch_weekly_elo(YEAR, week)
        if df is not None:
            save_path = os.path.join(SAVE_DIR, f"week_{week:02d}.csv")
            df.to_csv(save_path, index=False)
            print(f"✅ Saved: {save_path}")
        time.sleep(1)  # avoid hammering the API

if __name__ == "__main__":
    main()
