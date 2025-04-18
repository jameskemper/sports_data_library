import os
import pandas as pd

# Base folder with all year subfolders
base_folder = r"C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAA_football\season_stats\box_scores"

# Loop through each year
for year in range(2000, 2025):
    year_folder = os.path.join(base_folder, str(year))

    if not os.path.exists(year_folder):
        print(f"❌ Folder for {year} does not exist. Skipping.")
        continue

    csv_files = [f for f in os.listdir(year_folder) if f.endswith(".csv") and f.startswith("week")]

    for file in csv_files:
        file_path = os.path.join(year_folder, file)
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                os.remove(file_path)
                print(f"🗑️ Deleted EMPTY file: {file_path}")
        except pd.errors.EmptyDataError:
            os.remove(file_path)
            print(f"🗑️ Deleted UNREADABLE file (no columns): {file_path}")
        except Exception as e:
            print(f"⚠️ Skipped {file_path} due to unexpected error: {e}")
