import requests
import pandas as pd
import os
from datetime import datetime

# -------------------------------
# Auto-detect current WNBA season year
# -------------------------------
season = datetime.now().year
save_dir = os.path.join("WNBA", "player_stats_app", "data")
os.makedirs(save_dir, exist_ok=True)
output_file = os.path.join(save_dir, f"player_stats_season_{season}.csv")

# -------------------------------
# Download season stats table
# -------------------------------
url = f"https://www.espn.com/wnba/stats/player/_/season/{season}/seasontype/2"
print(f"Downloading WNBA season stats from {url}")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) "
        "Gecko/20100101 Firefox/123.0"
    )
}

resp = requests.get(url, headers=headers, timeout=30)
resp.raise_for_status()

# -------------------------------
# Parse tables
# -------------------------------
tables = pd.read_html(resp.text)
print(f"Found {len(tables)} tables on the page.")

players_df = tables[0]  # RK, Name
stats_df   = tables[1]  # POS, GP, ...

# Drop duplicate RK column from stats table if present
if "RK" in stats_df.columns:
    stats_df = stats_df.drop(columns="RK")

combined_df = pd.concat([players_df, stats_df], axis=1)

# Remove repeated header rows (ESPN pagination artifact)
combined_df = combined_df[combined_df["RK"] != "RK"]

combined_df.to_csv(output_file, index=False)
print(f"Saved {len(combined_df)} rows to {output_file}")
