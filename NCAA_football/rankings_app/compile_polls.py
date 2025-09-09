#!/usr/bin/env python3
"""
compile_polls.py

Compiles all weekly poll JSONs into a season-long CSV.
Handles both dict and list JSON root structures.
"""

import os
import json
import pandas as pd

YEAR = int(os.getenv("YEAR", 2025))
LAST_WEEK = 16

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"weekly_rankings_{YEAR}.csv")
FLAG_FILE = os.path.join(BASE_DIR, "polls_changed.flag")

def load_json(fname):
    """Load JSON and normalize root to a dict."""
    with open(fname, "r") as f:
        raw = json.load(f)
    # If root is a list, take the first element
    if isinstance(raw, list):
        if not raw:
            return {}
        return raw[0]
    return raw

def compile_all():
    rows = []
    for week in range(1, LAST_WEEK + 1):
        fname = os.path.join(WEEKS_DIR, f"week_{week:02}.json")
        if not os.path.exists(fname):
            print(f"❌ Week {week}: {fname} not found")
            continue

        print(f"📂 Processing {fname}")
        raw = load_json(fname)

        season = raw.get("season", YEAR)
        season_type = raw.get("seasonType", "regular")
        week_num = raw.get("week", week)

        polls = raw.get("polls", [])
        if not polls:
            print(f"⚠️ Week {week}: no polls found")
            continue

        for poll in polls:
            poll_name = poll.get("poll", "Unknown")
            for ranking in poll.get("ranks", []):
                rows.append({
                    "season": season,
                    "week": week_num,
                    "seasonType": season_type,
                    "poll": poll_name,
                    "rank": ranking.get("rank"),
                    "team": ranking.get("school"),
                    "conference": ranking.get("conference", ""),
                    "firstPlaceVotes": ranking.get("firstPlaceVotes"),
                    "points": ranking.get("points")
                })

    return pd.DataFrame(rows)

def main():
    df = compile_all()
    if df.empty:
        print("❌ No poll data compiled.")
        return

    # enforce consistent column order
    cols = [
        "season", "week", "seasonType", "poll",
        "rank", "team", "conference", "firstPlaceVotes", "points"
    ]
    df = df[cols]

    # sort for consistency
    df = df.sort_values(["week", "poll", "rank"]).reset_index(drop=True)

    # overwrite output
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Rebuilt {OUTPUT_FILE} with {len(df)} rows.")

    with open(FLAG_FILE, "w") as f:
        f.write("true")

if __name__ == "__main__":
    main()
