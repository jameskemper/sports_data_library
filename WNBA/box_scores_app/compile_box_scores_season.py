import pandas as pd
import os
import glob

# -------------------------------
# Paths
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))

# Folder with all your daily files
data_path = os.path.join(script_dir, "data", "2025")

# Master file will be saved here
output_file = os.path.join(script_dir, "data", "2025.csv")

# -------------------------------
# Load all CSV files
# -------------------------------
files = glob.glob(os.path.join(data_path, "*.csv"))
print(f"📂 Found {len(files)} CSV files to combine.")

all_dfs = []
for f in sorted(files):
    print(f"➕ Loading {os.path.basename(f)}...")
    try:
        df = pd.read_csv(f)
        all_dfs.append(df)
    except Exception as e:
        print(f"⚠️ Failed to load {f}: {e}")

# -------------------------------
# Combine into master DataFrame
# -------------------------------
if all_dfs:
    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df.drop_duplicates(inplace=True)
    master_df.to_csv(output_file, index=False)
    print(f"✅ Master dataset saved to {output_file} with {len(master_df)} rows.")
else:
    print(f"⚠️ No data combined. Check if CSVs exist in {data_path}")
