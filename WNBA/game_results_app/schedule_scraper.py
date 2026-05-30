import requests
import pandas as pd
import os
from datetime import datetime, timedelta

# -------------------------------
# Auto-detect current WNBA season year and date range
# WNBA season runs approximately May 1 - October 31
# -------------------------------
now         = datetime.now()
season_year = now.year
start_date  = datetime(season_year, 5, 1)
end_date    = datetime(season_year, 10, 31)

script_dir  = os.path.dirname(os.path.abspath(__file__))
save_path   = os.path.join(script_dir, "data")
os.makedirs(save_path, exist_ok=True)
output_file = os.path.join(save_path, f"schedule_{season_year}.csv")

print(f"Fetching WNBA {season_year} schedule ({start_date.date()} to {end_date.date()})...")

# -------------------------------
# Loop through season dates
# -------------------------------
all_games = []
current   = start_date
delta     = timedelta(days=1)

while current <= end_date:
    date_str = current.strftime("%Y%m%d")

    scoreboard_url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
        f"/scoreboard?dates={date_str}"
    )
    try:
        resp = requests.get(scoreboard_url, timeout=30)
        resp.raise_for_status()
        scoreboard = resp.json()
    except Exception as e:
        print(f"Failed to fetch {date_str}: {e}")
        current += delta
        continue

    for game in scoreboard.get("events", []):
        try:
            competition = game["competitions"][0]
            competitors = competition["competitors"]
            home = next(t for t in competitors if t["homeAway"] == "home")
            away = next(t for t in competitors if t["homeAway"] == "away")
            all_games.append({
                "Date":     current.strftime("%Y-%m-%d"),
                "Season":   season_year,
                "HomeTeam": home["team"]["shortDisplayName"],
                "AwayTeam": away["team"]["shortDisplayName"],
            })
        except Exception as e:
            print(f"Could not parse game on {date_str}: {e}")

    current += delta

# -------------------------------
# Save
# -------------------------------
if all_games:
    df = pd.DataFrame(all_games)
    df.drop_duplicates(inplace=True)
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} scheduled games to {output_file}")
else:
    print("No games found.")
