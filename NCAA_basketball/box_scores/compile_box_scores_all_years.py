import pandas as pd
import os

# --------------------------
# Configuration
# --------------------------
start_year = 2010
end_year = 2026

BASE_URL = "https://raw.githubusercontent.com/jameskemper/sports_data_library/refs/heads/master/NCAA_basketball/box_scores/"
OUTPUT_PATH = "NCAA_basketball/box_scores/box_scores_all.csv"

# --------------------------
# Compile All Seasons
# --------------------------
def main():
    all_dfs = []

    for year in range(start_year, end_year + 1):
        url = f"{BASE_URL}{year}.csv"
        print(f"Loading {url} ...")

        try:
            df = pd.read_csv(url)
            df["season"] = year  # ensure season column exists
            all_dfs.append(df)
            print(f"  → Loaded {len(df):,} rows")
        except Exception as e:
            print(f"  Could not load {year}: {e}")

    if not all_dfs:
        print("No files loaded. Exiting.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"\nTotal combined rows: {len(combined_df):,}")

    combined_df.drop_duplicates(inplace=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    combined_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved compiled box scores to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
