import os
import pandas as pd

# Base folder with your CSVs
BASE_DIR = r"C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAA_football\box_scores_app\data"

# Canonical schema: taken from 2025 file
canonical_file = os.path.join(BASE_DIR, "box_scores_2025.csv")
canonical_df = pd.read_csv(canonical_file)
canonical_columns = list(canonical_df.columns)

# Years to fix
years = list(range(2010, 2025))  # 2010 through 2024

for year in years:
    file_path = os.path.join(BASE_DIR, f"box_scores_{year}.csv")
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        continue

    df = pd.read_csv(file_path)

    # Drop any columns not in canonical schema
    df = df[[c for c in df.columns if c in canonical_columns]]

    # Add any missing columns with NaN
    for col in canonical_columns:
        if col not in df.columns:
            df[col] = pd.NA

    # Reorder to match canonical
    df = df[canonical_columns]

    # Save back (overwrites original)
    df.to_csv(file_path, index=False)
    print(f"✅ Standardized: {file_path}")

print("All files now match 2025 schema!")
