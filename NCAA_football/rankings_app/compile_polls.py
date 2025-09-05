#!/usr/bin/env python3
"""
compile_polls.py

Compiles all weekly poll JSONs into a season-long CSV.
Matches the exact format of weekly_rankings_2024.csv.
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

def compile_all():
    rows = []
    for week in range(1, LAST_WEEK + 1):
        fname = os.path.join(WEEKS_DIR, f"week_{week:02}.json")
        if not os.path.exists(fname):
            print(f"Week {week}: no data file found, skipping.")
            continue

        with open(fname, "r") as f:
            week_data = json.load(f)

        if not isinstance(week_data, list):
            print(f"Week {week}: unexpected format, skipping.")
            continue

        for poll in week_data:
            season = poll.get("season", YEAR)
            week_num = poll.get("week", week)
            season_type = poll.get("seasonType", "regular")
            poll_name = poll.get("poll", "Unknown")

            for ranking in poll.get("ranks", []):
                rows.append({
                    "season": season,
                    "week": week_num,
                    "seasonType": season_type,
                    "poll": poll_name,
                    "rank": ranking.get("rank"),
                    "school": ranking.get("school"),
                    "conference": ranking.get("conference", ""),
                    "firstPlaceVotes": ranking.get("firstPlaceVotes"),
                    "points": ranking.get("points")
                })

    return pd.DataFrame(rows)

def main():
    df = compile_all()
    if df.empty:
        print("No poll data compiled.")
        return

    # enforce exact column order like 2024
    cols = [
        "season",
        "week",
        "seasonType",
        "poll",
        "rank",
        "school",
        "conference",
        "firstPlaceVotes",
        "points"
    ]
    df = df[cols]

    # sort for consistency
    df = df.sort_values(["week", "poll", "rank"]).reset_index(drop=True)

    # make sure the output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # always overwrite
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Rebuilt {OUTPUT_FILE} with {len(df)} rows.")

    # flag so workflow commits
    with open(FLAG_FILE, "w") as f:
        f.write("true")

if __name__ == "__main__":
    main()

