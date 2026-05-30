import io
import requests
import pandas as pd
import os
import time
from datetime import datetime

# -------------------------------
# Auto-detect current WNBA season year
# -------------------------------
season = datetime.now().year
save_dir = os.path.join("WNBA", "player_stats_app", "data")
os.makedirs(save_dir, exist_ok=True)
output_file = os.path.join(save_dir, f"player_stats_season_{season}.csv")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) "
        "Gecko/20100101 Firefox/123.0"
    )
}

# -------------------------------
# Paginate ESPN stats pages
# ESPN shows 50 players per page.
# Page 1: base URL
# Page 2+: .../table/offensive/sort/avgPoints/dir/desc/page/N
# -------------------------------
def fetch_page(season: int, page: int) -> pd.DataFrame:
    if page == 1:
        url = (
            f"https://www.espn.com/wnba/stats/player"
            f"/_/season/{season}/seasontype/2"
        )
    else:
        url = (
            f"https://www.espn.com/wnba/stats/player"
            f"/_/season/{season}/seasontype/2"
            f"/table/offensive/sort/avgPoints/dir/desc/page/{page}"
        )

    print(f"  Fetching page {page}: {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    try:
        # Use StringIO to avoid pandas treating the HTML string as a file path
        tables = pd.read_html(io.StringIO(resp.text))
    except ValueError:
        return pd.DataFrame()

    if len(tables) < 2:
        return pd.DataFrame()

    players_df = tables[0].copy()  # RK, Name
    stats_df   = tables[1].copy()  # POS, GP, ...

    if "RK" in stats_df.columns:
        stats_df = stats_df.drop(columns="RK")

    combined = pd.concat([players_df, stats_df], axis=1)
    combined = combined[combined["RK"] != "RK"]
    combined = combined[combined["RK"].notna()]

    return combined


# -------------------------------
# Loop pages until empty or duplicate
# -------------------------------
print(f"Downloading WNBA {season} season stats (all pages)...")

all_pages = []
seen_ranks = set()
page = 1

while True:
    try:
        df_page = fetch_page(season, page)
    except Exception as e:
        print(f"  Error on page {page}: {e}")
        break

    if df_page.empty:
        print(f"  Page {page} returned no data — stopping.")
        break

    # Stop if we're seeing the same players (ESPN looping)
    current_ranks = set(df_page["RK"].astype(str).tolist())
    if current_ranks & seen_ranks:
        print(f"  Page {page} overlaps with previous — stopping.")
        break

    seen_ranks |= current_ranks
    all_pages.append(df_page)
    print(f"  Page {page}: {len(df_page)} players")

    if len(df_page) < 50:
        print(f"  Fewer than 50 rows — this is the last page.")
        break

    page += 1
    time.sleep(0.5)

# -------------------------------
# Combine and save
# -------------------------------
if all_pages:
    combined_df = pd.concat(all_pages, ignore_index=True)
    combined_df.drop_duplicates(subset=["RK"], inplace=True)
    combined_df["Season"] = season
    combined_df.to_csv(output_file, index=False)
    print(f"\nSaved {len(combined_df)} players to {output_file}")
else:
    print("No data collected.")
