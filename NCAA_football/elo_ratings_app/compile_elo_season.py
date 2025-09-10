#!/usr/bin/env python3
import os
import pandas as pd

YEAR = 2025
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUT_FILE = os.path.join(BASE_DIR, "data", f"elo_{YEAR}.csv")

def main():
    if not os.path.exists(WEEKS_DIR):
        print(f"⚠️ {WEEKS_DIR} does not exist. Run weekly_elo_scraper.py first.")
        return

    # Collect weekly CSVs
    weekly_files = [
        os.path.join(WEEKS_DIR, f) 
        for f in sorted(os.listdir(WEEKS_DIR)) 
        if f.endswith(".csv")
    ]

    if not weekly_files:
        print("⚠️ No weekly files found to compile yet.")
        return

    # Concatenate all weeks into one DataFrame
    df_list = []
    for f in weekly_files:
        try:
            df = pd.read_csv(f)
            df["week_file"] = os.path.basename(f)  # keep track of source week
            df_list.append(df)
        except Exception as e:
            print(f"❌ Error reading {f}: {e}")

    if not df_list:
        print("⚠️ No data compiled, all files were empty or errored.")
        return

    full_df = pd.concat(df_list, ignore_index=True)

    # Save compiled season file
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    full_df.to_csv(OUT_FILE, index=False)
    print(f"✅ Compiled season file saved to {OUT_FILE}")

if __name__ == "__main__":
    main()
