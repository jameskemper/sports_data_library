#!/usr/bin/env python3
"""
weekly_elo_scraper.py

Fetches weekly ELO ratings from the CFBD API and saves them as CSVs.
"""

import os
import pandas as pd
from cfbd import ApiClient, Configuration
from cfbd.api import RatingsApi

# Get API key from environment
CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    raise ValueError("Missing CFBD_API_KEY in environment variables.")

YEAR = 2025
SEASON_TYPE = "regular"
LAST_WEEK = 20  # Adjust if the season length changes

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
os.makedirs(WEEKS_DIR, exist_ok=True)

# Configure API client
config = Configuration()
config.api_key["Authorization"] = CFBD_API_KEY
config.api_key_prefix["Authorization"] = "Bearer"
api_client = ApiClient(config)
ratings_api = RatingsApi(api_client)

# Loop through weeks
for week in range(1, LAST_WEEK + 1):
    try:
        print(f"📅 Fetching {YEAR} Week {week} ELO ratings...")
        elo_data = ratings_api.get_elo_ratings(year=YEAR, week=week, season_type=SEASON_TYPE)

        if not elo_data:
            print(f"⚠️ No data found for Week {week}. Skipping.")
            continue

        # Convert to DataFrame
        df = pd.DataFrame([team.to_dict() for team in elo_data])

        # Save weekly CSV
        out_path = os.path.join(WEEKS_DIR, f"week_{week:02d}.csv")
        df.to_csv(out_path, index=False)
        print(f"✅ Saved {out_path}")

    except Exception as e:
        print(f"❌ Error fetching year {YEAR} week {week}: {e}")
