import pandas as pd
import os
import glob
from datetime import datetime

# -------------------------------
# Auto-detect current WNBA season year
# -------------------------------
season_year = datetime.now().year
script_dir  = os.path.dirname(os.path.abspath(__file__))
data_path   = os.path.join(script_dir, "data", str(season_year))
output_file = os.path.join(script_dir, "data", f"player_stats_{season_year}.csv")

# Normalize column names across old and new scraper versions
COLUMN_RENAMES = {
    "PlayerName": "Player",
    "Starter":    "Jersey",
}

FRONT_COLS = [
    "GameID", "Date", "Season", "Team", "PlayerID", "Player",
    "Position", "Jersey", "minutes", "points",
]

# -------------------------------
# Load all daily CSVs for this season
# -------------------------------
files = [f for f in sorted(glob.glob(os.path.join(data_path, "*.csv")))
         if os.path.getsize(f) > 0]
print(f"Found {len(files)} daily files for season {season_year}.")

all_dfs = []
for f in files:
    print(f"Loading {os.path.basename(f)}...")
    try:
        df = pd.read_csv(f)
        df.rename(columns=COLUMN_RENAMES, inplace=True)
        if "Season" not in df.columns:
            df["Season"] = season_year
        all_dfs.append(df)
    except Exception as e:
        print(f"  Skipped: {e}")

# -------------------------------
# Combine, reorder, and save
# -------------------------------
if all_dfs:
    master = pd.concat(all_dfs, ignore_index=True)
    master.drop_duplicates(inplace=True)

    existing_front = [c for c in FRONT_COLS if c in master.columns]
    remaining = [c for c in master.columns if c not in existing_front]
    master = master[existing_front + remaining]

    master.to_csv(output_file, index=False)
    print(f"Saved {len(master):,} rows to {output_file}")
else:
    print(f"No data found in {data_path}")
