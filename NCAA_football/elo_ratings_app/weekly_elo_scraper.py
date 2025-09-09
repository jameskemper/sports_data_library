import os
import cfbd
import pandas as pd

# ----- AUTH -----
api_key = os.getenv("CFBD_API_KEY")
if not api_key or not api_key.strip():
    raise SystemExit("CFBD_API_KEY not set. Exiting.")

configuration = cfbd.Configuration()
configuration.api_key["Authorization"] = api_key.strip()
configuration.api_key_prefix["Authorization"] = "Bearer"

api_client = cfbd.ApiClient(configuration)
games_api = cfbd.GamesApi(api_client)

year = 2025
season_type = "regular"

script_dir = os.path.dirname(os.path.abspath(__file__))
weekly_dir = os.path.join(script_dir, "data", f"weeks_{year}")
os.makedirs(weekly_dir, exist_ok=True)

# ---- loop through all weeks (1–20) ----
for week in range(1, 21):
    try:
        games = games_api.get_games(year=year, week=week, season_type=season_type)
    except Exception as e:
        print(f"Error fetching {year} week {week}: {e}")
        continue

    if not games:
        print(f"No games found for {year} week {week}.")
        continue

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

    df_week = pd.DataFrame(rows)
    if not df_week.empty:
        out_file = os.path.join(weekly_dir, f"week_{week}.csv")
        df_week.to_csv(out_file, index=False)
        print(f"Saved {year} week {week} → {out_file}")
    else:
        print(f"Week {week} had no data to save.")
