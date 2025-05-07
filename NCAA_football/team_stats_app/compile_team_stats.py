#!/usr/bin/env python3
"""
compile_team_stats.py

Reads per-week advanced stats CSVs from:
  .../data/weeks_<YEAR>/advanced_stats_week_<WW>.csv

Concatenates them into:
  .../data/weekly_advanced_stats_<YEAR>.csv
"""

import os
import pandas as pd

# Config
YEAR    = 2025
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(BASE_DIR, "data")
WEEKS_DIR = os.path.join(DATA_ROOT, f"weeks_{YEAR}")
OUTPUT_CSV = os.path.join(DATA_ROOT, f"weekly_advanced_stats_{YEAR}.csv")

def main():
    if not os.path.isdir(WEEKS_DIR):
        print(f"No weekly folder at {WEEKS_DIR}")
        return

    dfs = []
    for fn in sorted(os.listdir(WEEKS_DIR)):
        if not fn.endswith(".csv"):
            continue
        wk = int(fn.split("_")[-1].split(".")[0])
        path = os.path.join(WEEKS_DIR, fn)
        df = pd.read_csv(path)
        df["week"] = wk
        dfs.append(df)
        print(f"Loaded week {wk}: {len(df)} rows")

    if not dfs:
        print("No weekly files to compile.")
        return

    full = pd.concat(dfs, ignore_index=True)
    full.sort_values(["week", "team"], inplace=True)

    os.makedirs(DATA_ROOT, exist_ok=True)
    full.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote combined CSV: {OUTPUT_CSV} ({len(full)} rows)")

if __name__ == "__main__":
    main()
