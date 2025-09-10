#!/usr/bin/env python3
"""
compile_elo_season.py

Compile weekly ELO JSON files into one CSV per year.
"""

import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_week(week_file):
    """Load one week's JSON and flatten into DataFrame."""
    with open(week_file, "r") as f:
        data = json.load(f)

    if not data:
        return pd.DataFrame()

    df = pd.json_normalize(data)
    df["week"] = int(os.path.basename(week_file).split("_")[1].split(".")[0])
    return df

def compile_year(year: int):
    """Compile all weekly files for a given year."""
    data_dir = os.path.join(BASE_DIR, "data", f"weeks_{year}")
    output_file = os.path.join(BASE_DIR, "data", f"elo_{year}.csv")

    if not os.path.exists(data_dir):
        print(f"⚠️ No weekly directory found for {year}")
        return

    all_files = sorted(
        [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".json")]
    )

    if not all_files:
        print(f"⚠️ No weekly files found for {year}")
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
        final_df.to_csv(output_file, index=False)
        print(f"✅ Compiled season file saved to {output_file}")
    else:
        print(f"⚠️ No data compiled for {year}")

def main():
    for year in range(2010, 2025):  # loop 2010 → 2024
        compile_year(year)

if __name__ == "__main__":
    main()
