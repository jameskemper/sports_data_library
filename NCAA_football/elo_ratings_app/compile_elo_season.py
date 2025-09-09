import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
weeks_folder = os.path.join(data_dir, "weeks_2025")

os.makedirs(weeks_folder, exist_ok=True)

weekly_files = sorted(
    os.path.join(weeks_folder, f)
    for f in os.listdir(weeks_folder)
    if f.endswith(".csv")
)

if not weekly_files:
    print("No weekly files found to compile.")
    raise SystemExit(0)

dfs = [pd.read_csv(f) for f in weekly_files if os.path.getsize(f) > 0]

if not dfs:
    print("All weekly files were empty.")
    raise SystemExit(0)

combined = pd.concat(dfs, ignore_index=True)
combined_file = os.path.join(data_dir, "elo_ratings_2025.csv")
combined.to_csv(combined_file, index=False)
print(f"Compiled season file saved to {combined_file}")
