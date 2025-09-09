import os
import pandas as pd

# Base directory = directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
weeks_folder = os.path.join(data_dir, "weeks_2025")

# Ensure folder exists so os.listdir doesn't blow up
os.makedirs(weeks_folder, exist_ok=True)

weekly_files = sorted(
    os.path.join(weeks_folder, f)
    for f in os.listdir(weeks_folder)
    if f.endswith(".csv")
)

dfs = []
for file in weekly_files:
    df = pd.read_csv(file)
    if not df.empty:
        dfs.append(df)

if not dfs:
    print("No weekly files found to compile.")
    raise SystemExit(0)

combined = pd.concat(dfs, ignore_index=True)
combined_filename = os.path.join(data_dir, "elo_ratings_2025.csv")
combined.to_csv(combined_filename, index=False)
print(f"Compiled season file saved to {combined_filename}")
