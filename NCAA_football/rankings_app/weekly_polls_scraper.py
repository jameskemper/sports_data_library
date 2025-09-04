#!/usr/bin/env python3
"""
compile_polls.py

Reads all 16 week JSONs and compiles into a single season CSV.
Only updates the CSV if something changed (based on hash).
"""

import os
import json
import pandas as pd
import hashlib

YEAR = int(os.getenv("YEAR", 2025))
LAST_WEEK = 16

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"polls_{YEAR}.csv")

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

    # Compare hashes to avoid unnecessary commits
    new_hash = hashlib.md5(df.to_csv(index=False).encode()).hexdigest()
    old_hash = None
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "rb") as f:
            old_hash = hashlib.md5(f.read()).hexdigest()

    if old_hash == new_hash:
        print("No change in compiled polls.")
    else:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Compiled polls saved to {OUTPUT_FILE}")
        with open(os.path.join(BASE_DIR, "polls_changed.flag"), "w") as f:
            f.write("true")

if __name__ == "__main__":
    main()
