import pandas as pd
import os

# --------------------------
# Configuration
# --------------------------
start_year = 2010
end_year = 2026

# Use local directory path instead of GitHub URL
INPUT_PATH = "NCAA_basketball/box_scores/"
OUTPUT_PATH = "NCAA_basketball/box_scores/box_scores_all.csv"

# --------------------------
# Compile All Seasons
# --------------------------
def main():
    all_dfs = []

    for year in range(start_year, end_year + 1):
        filepath = f"{INPUT_PATH}{year}.csv"
        print(f"Loading {filepath} ...")

        try:
            # Check if file exists
            if not os.path.exists(filepath):
                print(f"  File not found: {filepath}")
                continue
                
            df = pd.read_csv(filepath)
            
            # Add season column if it doesn't exist
            if "season" not in df.columns:
                df["season"] = year
            
            all_dfs.append(df)
            print(f"  → Loaded {len(df):,} rows")
        except Exception as e:
            print(f"  Could not load {year}: {e}")

    if not all_dfs:
        print("No files loaded. Exiting.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"\nTotal combined rows: {len(combined_df):,}")

    # Remove duplicates
    initial_count = len(combined_df)
    combined_df.drop_duplicates(inplace=True)
    duplicates_removed = initial_count - len(combined_df)
    print(f"Removed {duplicates_removed:,} duplicate rows")
    print(f"Final row count: {len(combined_df):,}")

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    # Save to CSV
    combined_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved compiled box scores to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
