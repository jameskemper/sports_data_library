#!/usr/bin/env python3
"""
compile_polls.py

Reads all 16 week JSONs and compiles into a single season CSV.
Always updates the CSV if new data exists.
"""

import os
import json
import pandas as pd
import hashlib

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
            continue

        with open(fname, "r") as f:
            week_data = json.load(f)

        if not isinstance(week_data, list):
            continue

        for poll in week_data:
            poll_name = poll.get("poll", "Unknown")
            for ranking in poll.get("ranks", []):
                rows.append({
                    "year": YEAR,
                    "week": week,
                    "poll": poll_name,
                    "rank": ranking.get("rank"),
                    "school": ranking.get("school"),
                    "conference": ranking.get("conference", ""),
                    "first_place_votes": ranking.get("firstPlaceVotes", None),
                    "points": ranking.get("points", None)
                })

    return pd.DataFrame(rows)

def main():
    df = compile_all()
    if df.empty:
        print("No poll data compiled.")
        return

    # New file content
    csv_content = df.to_csv(index=False)

    # Compare hashes
    new_hash = hashlib.md5(csv_content.encode()).hexdigest()
    old_hash = None
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "rb") as f:
            old_hash = hashlib.md5(f.read()).hexdigest()

    if old_hash == new_hash:
        print("No change in weekly rankings CSV.")
    else:
        with open(OUTPUT_FILE, "w") as f:
            f.write(csv_content)
        print(f"Updated {OUTPUT_FILE}")
        with open(FLAG_FILE, "w") as f:
            f.write("true")

if __name__ == "__main__":
    main()
