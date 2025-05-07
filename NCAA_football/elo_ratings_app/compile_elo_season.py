import pandas as pd
import os

# Base directory = directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
weeks_folder = os.path.join(data_dir, "weeks_2025")

# Gather all weekly CSV files
weekly_files = [os.path.join(weeks_folder, f) for f in os.listdir(weeks_folder) if f.endswith('.csv')]

# Combine all weekly DataFrames
dfs = []
for file in sorted(weekly_files):
    df = pd.read_csv(file)
    dfs.append(df)

# Save combined file
if dfs:
    combined = pd.concat(dfs, ignore_index=True)
    combined_filename = os.path.join(data_dir, "elo_ratings_2025.csv")
    combined.to_csv(combined_filename, index=False)
    print(f"Compiled season file saved to {combined_filename}")
else:
    print("No weekly files found to compile.")
