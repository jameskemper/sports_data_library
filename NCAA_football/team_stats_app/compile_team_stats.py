import os
import glob
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YEAR = os.environ.get("YEAR", "2025")
DATA_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{YEAR}.csv")

def compile_weekly_stats():
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "advanced_stats_week_*.csv")))
    df_list = []

    for f in all_files:
        # pull week from filename (e.g., advanced_stats_week_03.csv → 3)
        fname = os.path.basename(f)
        week = int(fname.split("_")[-1].replace(".csv", ""))

        df = pd.read_csv(f)
        df.insert(0, "week", week)   # add week as the first column
        df_list.append(df)

    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        combined.to_csv(OUTPUT_FILE, index=False)
        print(f"Compiled {len(df_list)} weeks into {OUTPUT_FILE}")
    else:
        print("No weekly files found to compile.")

if __name__ == "__main__":
    compile_weekly_stats()
