#!/usr/bin/env python3
"""
compile_polls.py

Reads all weekly JSON files from
  {BASE_DIR}/data/weeks_{YEAR}/week_##.json
flattens/cleans them into one season CSV:
  {BASE_DIR}/data/weekly_rankings_<YEAR>.csv

Renames "school" → "team".
"""

import os
import json
import pandas as pd

YEAR      = 2025  # <- updated to reflect current season

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_CSV  = os.path.join(BASE_DIR, "data", f"weekly_rankings_{YEAR}.csv")

def flatten_week(json_data, week: int) -> pd.DataFrame:
    rows = []
    for entry in json_data:
        season     = entry.get("season")
        seasonType = entry.get("seasonType")
        for poll in entry.get("polls", []):
            poll_name = poll.get("poll")
            for r in poll.get("ranks", []):
                rows.append({
                    "season"    : season,
                    "seasonType": seasonType,
                    "week"      : week,
                    "poll"      : poll_name,
                    "rank"      : r.get("rank"),
                    "team"      : r.get("school"),
                    "conference": r.get("conference"),
                    "points"    : r.get("points"),
                })
    return pd.DataFrame(rows)

def main():
    if not os.path.isdir(WEEKS_DIR):
        print(f"No weekly folder found at {WEEKS_DIR}")
        return

    all_dfs = []
    for fname in sorted(os.listdir(WEEKS_DIR)):
        if not fname.lower().endswith(".json"):
            continue
        wk = int(fname.replace("week_", "").replace(".json", ""))
        path = os.path.join(WEEKS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = flatten_week(data, wk)
        print(f" Week {wk:02d}: {len(df)} rows")
        all_dfs.append(df)

    if not all_dfs:
        print("No JSON files to compile.")
        return

    full = pd.concat(all_dfs, ignore_index=True)
    full.drop_duplicates(subset=["week","poll","team"], inplace=True)
    full.sort_values(["week","poll","rank"], inplace=True)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    full.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved combined CSV to:\n  {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
