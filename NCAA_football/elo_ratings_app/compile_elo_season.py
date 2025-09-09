#!/usr/bin/env python3
"""
compile_elo_season.py

Compile weekly ELO JSON files into a single CSV.
"""

import os
import json
import pandas as pd

YEAR = 2025

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"elo_{YEAR}.csv")

def load_week(week_file):
    """Load one week's JSON and flatten into DataFrame."""
    with open(week_file, "r") as f:
        data = json.load(f)

    if not data:
        return pd.DataFrame()

    df = pd.json_normalize(data)
    df["week"] = int(os.path.basename(week_file).split("_")[1].split(".")[0])
    return df

def main():
    if not os.path.exists(DATA_DIR):
        print(f"⚠️ No weekly directory found for {YEAR}")
        return

    all_files = sorted(
        [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    )

    if not all_files:
        print("⚠️ No weekly files found to compile yet.")
        return

    dfs = []
    for f in all_files:
        try:
            df = load_week(f)
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"⚠️ Could not load {f}: {e}")

    if dfs:
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Compiled season file saved to {OUTPUT_FILE}")
    else:
        print("⚠️ No data to compile.")

if __name__ == "__main__":
    main()
