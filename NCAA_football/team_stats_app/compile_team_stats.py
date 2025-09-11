import os
import glob
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def compile_weekly_stats_for_year(year):
    data_dir = os.path.join(BASE_DIR, "data", f"weeks_{year}")
    output_file = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{year}.csv")

    all_files = sorted(glob.glob(os.path.join(data_dir, "advanced_stats_week_*.csv")))
    df_list = []

    for f in all_files:
        # extract week from filename
        fname = os.path.basename(f)
        week = int(fname.split("_")[-1].replace(".csv", ""))

        df = pd.read_csv(f)
        df.insert(0, "week", week)
        df_list.append(df)

    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        combined.to_csv(output_file, index=False)
        print(f"Compiled {len(df_list)} weeks into {output_file}")
    else:
        print(f"No weekly files found for {year}")

def main():
    for year in range(2010, 2025):  # 2010–2024 inclusive
        compile_weekly_stats_for_year(year)

if __name__ == "__main__":
    main()
