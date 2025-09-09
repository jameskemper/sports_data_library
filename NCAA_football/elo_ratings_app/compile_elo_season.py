import pandas as pd
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
weeks_folder = os.path.join(data_dir, "weeks_2025")
os.makedirs(weeks_folder, exist_ok=True)

weekly_files = [
    os.path.join(weeks_folder, f)
    for f in os.listdir(weeks_folder)
    if f.endswith(".csv")
]

if not weekly_files:
    print("⚠️ No weekly files found to compile yet.")
else:
    dfs = [pd.read_csv(f) for f in sorted(weekly_files)]
    combined = pd.concat(dfs, ignore_index=True)

    # Ensure chronological order
    combined.sort_values(by=["week", "season"], inplace=True)

    combined_filename = os.path.join(data_dir, "elo_ratings_2025.csv")
    combined.to_csv(combined_filename, index=False)
    print(f"✅ Compiled season file saved → {combined_filename}")
