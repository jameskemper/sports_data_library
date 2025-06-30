import requests
import pandas as pd
import os
from datetime import datetime, timedelta

# -------------------------------
# Paths
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "data")
os.makedirs(save_path, exist_ok=True)
output_file = os.path.join(save_path, "schedule_2025.csv")

# -------------------------------
# Loop through season dates
# -------------------------------
start_date = datetime(2025, 5, 16)
end_date = datetime(2025, 10, 30)
delta = timedelta(days=1)

all_games = []

while start_date <= end_date:
    date_str = start_date.strftime("%Y%m%d")
    print(f"📅 Processing {date_str}...")

    # Get ESPN scoreboard
    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(scoreboard_url, timeout=30)
        resp.raise_for_status()
        scoreboard = resp.json()
    except Exception as e:
        print(f"⚠️ Failed to fetch scoreboard for {date_str}: {e}")
        start_date += delta
        continue

    # Extract scheduled games
    games = scoreboard.get('events', [])
    for game in games:
        try:
            competition = game['competitions'][0]
            competitors = competition['competitors']
            home = next(team for team in competitors if team['homeAway'] == 'home')
            away = next(team for team in competitors if team['homeAway'] == 'away')
            all_games.append({
                'Date': start_date.strftime("%Y-%m-%d"),
                'HomeTeam': home['team']['shortDisplayName'],
                'AwayTeam': away['team']['shortDisplayName'],
            })
        except Exception as e:
            print(f"⚠️ Could not parse a game on {date_str}: {e}")

    start_date += delta

# -------------------------------
# Save to master CSV
# -------------------------------
if all_games:
    df = pd.DataFrame(all_games)
    df.drop_duplicates(inplace=True)
    df.to_csv(output_file, index=False)
    print(f"✅ Full season schedule saved to {output_file} with {len(df)} games.")
else:
    print("⚠️ No games data collected.")
