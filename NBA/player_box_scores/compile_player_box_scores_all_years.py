import os
import pandas as pd

# --------------------------
# Configuration
# --------------------------
START_YEAR  = 2010
END_YEAR    = 2026
INPUT_DIR   = "NBA/player_box_scores"
OUTPUT_PATH = "NBA/player_box_scores/player_box_scores_all.csv"


def main():
    all_dfs = []

    for year in range(START_YEAR, END_YEAR + 1):
        filepath = os.path.join(INPUT_DIR, f"{year}.csv")
        print(f"Loading {filepath} ...")

        if not os.path.exists(filepath):
            print(f"  File not found: {filepath}")
            continue

        try:
            df = pd.read_csv(filepath)
            if "season" not in df.columns:
                df["season"] = year
            all_dfs.append(df)
            print(f"  -> Loaded {len(df):,} rows")
        except Exception as e:
            print(f"  Could not load {year}: {e}")

    if not all_dfs:
        print("No files loaded. Exiting.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\nTotal combined rows: {len(combined):,}")

    initial = len(combined)
    combined.drop_duplicates(subset=["gameId", "playerId"], inplace=True)
    print(f"Removed {initial - len(combined):,} duplicates")
    print(f"Final row count: {len(combined):,}")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved compiled player box scores -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
