import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# -------------------------------
# Season year helper
# WNBA season runs May-October.
# Use the calendar year of the game date as the season year.
# -------------------------------
def get_season_year(dt: datetime) -> int:
    return dt.year

# -------------------------------
# Setup
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))

central = ZoneInfo("America/Chicago")
yesterday = datetime.now(central) - timedelta(days=1)
season_year = get_season_year(yesterday)

save_path = os.path.join(script_dir, "data", str(season_year))
os.makedirs(save_path, exist_ok=True)

date_str = yesterday.strftime("%Y%m%d")           # ESPN format: 20250516
filename_date = yesterday.strftime("%m_%d_%Y")    # file name:   05_16_2025

print(f"Collecting WNBA box scores for {yesterday.strftime('%Y-%m-%d')} (season {season_year})...")

# -------------------------------
# Get scoreboard
# -------------------------------
scoreboard_url = (
    f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
    f"/scoreboard?dates={date_str}"
)
resp = requests.get(scoreboard_url, timeout=30)
resp.raise_for_status()
scoreboard = resp.json()

game_ids = [event["id"] for event in scoreboard.get("events", [])]

if not game_ids:
    print(f"No games found for {date_str}.")
    exit(0)

print(f"Found {len(game_ids)} games.")

# -------------------------------
# Fetch box scores
# -------------------------------
all_team_stats = []

for i, game_id in enumerate(game_ids, 1):
    print(f"Fetching box score for GameID {game_id} ({i}/{len(game_ids)})...")
    summary_url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
        f"/summary?event={game_id}"
    )
    try:
        resp = requests.get(summary_url, timeout=30)
        resp.raise_for_status()
        summary = resp.json()

        teams = summary["boxscore"]["teams"]
        for team in teams:
            stats_flat = {
                "GameID":    game_id,
                "Date":      yesterday.strftime("%Y-%m-%d"),
                "Season":    season_year,
                "TeamName":  team["team"]["shortDisplayName"],
            }
            for stat in team["statistics"]:
                stats_flat[stat["name"]] = stat["displayValue"]
            all_team_stats.append(stats_flat)
    except Exception as e:
        print(f"Failed to extract stats for GameID {game_id}: {e}")

# -------------------------------
# Build and clean DataFrame
# -------------------------------
if not all_team_stats:
    print("No box score data collected.")
    exit(0)

df = pd.DataFrame(all_team_stats)

# Split combined shot columns into made/attempted
split_cols = {
    "fieldGoalsMade-fieldGoalsAttempted":                        ("FGM",  "FGA"),
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted":    ("3PM",  "3PA"),
    "freeThrowsMade-freeThrowsAttempted":                        ("FTM",  "FTA"),
}
for src, (made, att) in split_cols.items():
    if src in df.columns:
        df[[made, att]] = df[src].str.split("-", expand=True).astype(int)
        df.drop(columns=src, inplace=True)

# Reorder
front_cols = [
    "GameID", "Date", "Season", "TeamName",
    "FGM", "FGA", "fieldGoalPct",
    "3PM", "3PA", "threePointFieldGoalPct",
    "FTM", "FTA", "freeThrowPct",
    "totalRebounds", "offensiveRebounds", "defensiveRebounds",
    "assists", "steals", "blocks", "turnovers",
    "personalFouls", "points", "fastBreakPoints",
    "pointsInPaint", "largestLead",
]
existing_front = [c for c in front_cols if c in df.columns]
df = df[existing_front + [c for c in df.columns if c not in existing_front]]

# -------------------------------
# Save
# -------------------------------
file_path = os.path.join(save_path, f"{filename_date}.csv")
df.to_csv(file_path, index=False)
print(f"Saved {len(df)} rows to {file_path}")
