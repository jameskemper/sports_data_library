import os
import time
import datetime
import pandas as pd
import cfbd

# ----- AUTH GUARD -----
api_key = os.getenv("CFBD_API_KEY")
if not api_key or not api_key.strip():
    print("CFBD_API_KEY is not set. Exiting without scraping.")
    raise SystemExit(0)

configuration = cfbd.Configuration()
# cfbd client expects 'Authorization' with 'Bearer' prefix defined here:
configuration.api_key["Authorization"] = api_key.strip()
configuration.api_key_prefix["Authorization"] = "Bearer"

api_client = cfbd.ApiClient(configuration)
games_api = cfbd.GamesApi(api_client)

# ----- WEEK SELECTION (rough ISO→CFB mapping) -----
today = datetime.date.today()
year = 2025
week = today.isocalendar()[1] - 32
week = max(1, min(week, 20))

print(f"Fetching {year} Week {week} games...")

try:
    games = games_api.get_games(year=year, week=week)
except Exception as e:
    print(f"Error fetching year {year} week {week}: {e}")
    time.sleep(1)
    games = []

if not games:
    print(f"No games found for year {year}, week {week}.")
    raise SystemExit(0)

rows = []
for g in games:
    rows.append({
        "season": g.season,
        "week": g.week,
        "home_team": g.home_team,
        "home_id": g.home_id,
        "home_conference": g.home_conference,
        "home_points": g.home_points,
        "home_pregame_elo": g.home_pregame_elo,
        "home_postgame_elo": g.home_postgame_elo,
        "away_team": g.away_team,
        "away_id": g.away_id,
        "away_conference": g.away_conference,
        "away_points": g.away_points,
        "away_pregame_elo": g.away_pregame_elo,
        "away_postgame_elo": g.away_postgame_elo,
        "conference_game": int(g.conference_game),
    })

df_week = pd.DataFrame.from_records(rows)

if df_week.empty:
    print(f"No valid data returned for {year} week {week}.")
    raise SystemExit(0)

df_week["margin"] = df_week["home_points"] - df_week["away_points"]

script_dir = os.path.dirname(os.path.abspath(__file__))
weekly_dir = os.path.join(script_dir, "data", "weeks_2025")
os.makedirs(weekly_dir, exist_ok=True)

weekly_filename = os.path.join(weekly_dir, f"week_{week}.csv")
df_week.to_csv(weekly_filename, index=False)
print(f"Week {week} data saved to {weekly_filename}")
