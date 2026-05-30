import pandas as pd
import os
import glob
from datetime import datetime

# -------------------------------
# Auto-detect current WNBA season year
# -------------------------------
def get_season_year() -> int:
    return datetime.now().year

season_year = get_season_year()
script_dir  = os.path.dirname(os.path.abspath(__file__))
data_path   = os.path.join(script_dir, "data", str(season_year))
output_file = os.path.join(script_dir, "data", f"boxscores_{season_year}.csv")

# -------------------------------
# Load all daily CSVs for this season
# -------------------------------
files = sorted(glob.glob(os.path.join(data_path, "*.csv")))
print(f"Found {len(files)} daily files for season {season_year}.")

all_dfs = []
for f in files:
    print(f"Loading {os.path.basename(f)}...")
    try:
        all_dfs.append(pd.read_csv(f))
    except Exception as e:
        print(f"Failed to load {f}: {e}")

# -------------------------------
# Combine and save
# -------------------------------
if all_dfs:
    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df.drop_duplicates(inplace=True)
    master_df.to_csv(output_file, index=False)
    print(f"Saved {len(master_df)} rows to {output_file}")
else:
    print(f"No data found in {data_path}")
