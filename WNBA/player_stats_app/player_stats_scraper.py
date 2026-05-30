import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# -------------------------------
# Setup
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))

central   = ZoneInfo("America/Chicago")
yesterday = datetime.now(central) - timedelta(days=1)
season_year = yesterday.year

save_path = os.path.join(script_dir, "data", str(season_year))
os.makedirs(save_path, exist_ok=True)

date_str      = yesterday.strftime("%Y%m%d")    # ESPN format: 20250516
filename_date = yesterday.strftime("%m_%d_%Y")  # file name:   05_16_2025

print(f"Collecting WNBA player stats for {yesterday.strftime('%Y-%m-%d')} (season {season_year})...")

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
# Collect player-level stats
# -------------------------------
all_player_stats = []

for i, game_id in enumerate(game_ids, 1):
    print(f"Fetching player stats for GameID {game_id} ({i}/{len(game_ids)})...")
    summary_url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
        f"/summary?event={game_id}"
    )
    try:
        resp = requests.get(summary_url, timeout=30)
        resp.raise_for_status()
        summary = resp.json()

        players_section = summary["boxscore"]["players"]
        for team_data in players_section:
            team_name  = team_data["team"]["shortDisplayName"]
            stats_info = team_data.get("statistics", [])[0]
            stat_keys  = stats_info["keys"]

            for athlete in stats_info["athletes"]:
                if athlete.get("didNotPlay"):
                    continue

                player_info = athlete["athlete"]
                stats_line  = athlete.get("stats", [])

                record = {
                    "GameID":    game_id,
                    "Date":      yesterday.strftime("%Y-%m-%d"),
                    "Season":    season_year,
                    "Team":      team_name,
                    "PlayerID":  player_info.get("id"),
                    "Player":    player_info.get("displayName"),
                    "Position":  player_info.get("position", {}).get("abbreviation"),
                    "Jersey":    player_info.get("jersey"),
                }
                for key, value in zip(stat_keys, stats_line):
                    record[key] = value

                all_player_stats.append(record)
    except Exception as e:
        print(f"Failed to extract player stats for GameID {game_id}: {e}")

# -------------------------------
# Save DataFrame
# -------------------------------
if not all_player_stats:
    print(f"No player stats collected for {date_str}.")
    exit(0)

df = pd.DataFrame(all_player_stats)

front_cols = [
    "GameID", "Date", "Season", "Team", "PlayerID", "Player", "Position", "Jersey",
    "minutes",
    "fieldGoalsMade-fieldGoalsAttempted",
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
    "freeThrowsMade-freeThrowsAttempted",
    "offensiveRebounds", "defensiveRebounds", "rebounds",
    "assists", "steals", "blocks", "turnovers", "fouls", "plusMinus", "points",
]
existing_front = [c for c in front_cols if c in df.columns]
df = df[existing_front + [c for c in df.columns if c not in existing_front]]

file_path = os.path.join(save_path, f"{filename_date}.csv")
df.to_csv(file_path, index=False)
print(f"Saved {len(df)} player rows to {file_path}")
