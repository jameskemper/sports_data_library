import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# -------------------------------
# Setup
# -------------------------------
script_dir  = os.path.dirname(os.path.abspath(__file__))
central     = ZoneInfo("America/Chicago")
yesterday   = datetime.now(central) - timedelta(days=1)
season_year = yesterday.year

save_path   = os.path.join(script_dir, "data")
os.makedirs(save_path, exist_ok=True)
output_file = os.path.join(save_path, f"game_results_{season_year}.csv")

date_str = yesterday.strftime("%Y%m%d")
print(f"Collecting WNBA game results for {yesterday.strftime('%Y-%m-%d')} (season {season_year})...")

# -------------------------------
# Fetch yesterday's scoreboard
# -------------------------------
scoreboard_url = (
    f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
    f"/scoreboard?dates={date_str}"
)
try:
    resp = requests.get(scoreboard_url, timeout=30)
    resp.raise_for_status()
    scoreboard = resp.json()
except Exception as e:
    print(f"Failed to fetch scoreboard: {e}")
    exit(1)

# -------------------------------
# Parse games
# -------------------------------
new_games = []
for game in scoreboard.get("events", []):
    try:
        competition = game["competitions"][0]
        competitors = competition["competitors"]
        home = next(t for t in competitors if t["homeAway"] == "home")
        away = next(t for t in competitors if t["homeAway"] == "away")
        new_games.append({
            "Date":      yesterday.strftime("%Y-%m-%d"),
            "Season":    season_year,
            "HomeTeam":  home["team"]["shortDisplayName"],
            "HomeScore": home.get("score"),
            "AwayTeam":  away["team"]["shortDisplayName"],
            "AwayScore": away.get("score"),
            "Status":    game.get("status", {}).get("type", {}).get("description", ""),
        })
    except Exception as e:
        print(f"Could not parse a game: {e}")

if not new_games:
    print(f"No games found for {date_str}.")
    exit(0)

df_new = pd.DataFrame(new_games)

# -------------------------------
# Append to existing CSV
# -------------------------------
if os.path.exists(output_file):
    df_existing = pd.read_csv(output_file)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam"], inplace=True)
    df_combined.to_csv(output_file, index=False)
    print(f"Appended {len(df_new)} games. Total: {len(df_combined)} -> {output_file}")
else:
    df_new.to_csv(output_file, index=False)
    print(f"Saved {len(df_new)} games to {output_file}")
