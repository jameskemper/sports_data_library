#!/usr/bin/env python3
"""
weekly_polls_scraper.py

Fetches CFBD weekly poll data for one week (auto-increment or specified),
and saves raw JSON to data/weeks_<YEAR>/week_##.json.
Ensures each saved file is a dict, not a list.
"""

import os
import json
import requests

API_KEY     = os.environ["CFBD_API_KEY"]
YEAR        = int(os.getenv("YEAR", 2025))
SEASON_TYPE = "regular"
LAST_WEEK   = 16

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
os.makedirs(WEEKS_DIR, exist_ok=True)

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def fetch_week(week):
    """Fetch poll data for a given week."""
    url = f"https://api.collegefootballdata.com/rankings?year={YEAR}&week={week}&seasonType={SEASON_TYPE}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ Week {week}: API error {resp.status_code}")
        return None

    data = resp.json()
    if not data:
        return None

    # normalize: if it's a list, flatten to first element
    if isinstance(data, list):
        data = data[0]

    return data

def save_week(week, data):
    """Save week data to JSON file."""
    fname = os.
