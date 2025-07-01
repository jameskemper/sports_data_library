import pandas as pd
import os

# -------------------------------
# Paths
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "data")
os.makedirs(save_path, exist_ok=True)
file_path = os.path.join(save_path, "player_stats_season_2025.csv")

# -------------------------------
# URL for 2025 season stats (update if ESPN changes structure)
# -------------------------------
url = "https://www.espn.com/wnba/stats/player/_/season/2025/seasontype/2"

print(f"📈 Downloading WNBA season stats from {url}")

# -------------------------------
# Use pandas to read HTML tables
# -------------------------------
tables = pd.read_html(url)

# Try to find the main player stats table
season_stats_df = None
for table in tables:
    # Typically will have columns like "PLAYER", "TEAM", "GP", "MIN", "PTS"
    if "PLAYER" in table.columns and "PTS" in table.columns:
        season_stats_df = table
        break

if season_stats_df is None:
    print("⚠️ Could not find a valid player stats table on the page.")
else:
    # -------------------------------
    # Clean up
    # -------------------------------
    # ESPN often repeats header rows inside the table — drop them
    season_stats_df = season_stats_df[season_stats_df["PLAYER"] != "PLAYER"]
    season_stats_df.reset_index(drop=True, inplace=True)

    # Save CSV
    season_stats_df.to_csv(file_path, index=False)
    print(f"✅ Saved season player stats to {file_path} with {len(season_stats_df)} rows.")
