#!/usr/bin/env python3
"""
compile_polls.py

Reads all week JSONs and compiles into a single season CSV.
Only updates the CSV if something changed (based on hash).
"""

import os
import json
import pandas as pd
import hashlib

YEAR = int(os.getenv("YEAR", 2025))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"polls_{YEAR}.csv")

def compile_all():
    rows = []
    for fname in sorted(os.listdir(WEEKS_DIR)):
        if fname.endswith(".json"):
            path = os.path.join(WEEKS_DIR, fname)
            with open(path, "r") as f:
                week_data = json.load(f)
            for poll in week_data.get("polls", []):
                for ranking in poll.get("ranks", []):
                    rows.append({
                        "week": int(fname.split("_")[1].split(".")[0]),
                        "poll": poll["poll"],
                        "rank": ranking["rank"],
                        "school": ranking["school"],
                        "conference": ranking.get("conference", "")
                    })
    return pd.DataFrame(rows)

def main():
    df = compile_all()
    if df.empty:
        print("No poll data found.")
        return

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
