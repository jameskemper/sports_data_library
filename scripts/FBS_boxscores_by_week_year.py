import os
import requests
import pandas as pd
import time
from datetime import datetime

# --- API Details ---
API_KEY = 'zNmyTjCEh+r3C0Tg49VDiwiqo58mcIP6AwY12Cf9E981x0y0L+mEiwTRHrR0a3eN'
BASE_URL = 'https://api.collegefootballdata.com/games'
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "accept": "application/json"
}

# --- Local Save Directory ---
BASE_DIR = r'C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAA_football\season_stats\box_scores'

def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def fetch_games(year, week):
    """ Fetch games for a given year and week """
    params = {
        "year": year,
        "week": week,
        "seasonType": "regular"
    }
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ⚠️ Failed to fetch {year} week {week} (Status: {response.status_code})")
            return []
    except Exception as e:
        print(f"  ❌ Exception fetching {year} week {week}: {e}")
        return []

def process_games(games):
    """ Convert list of games to DataFrame rows """
    game_data = []
    for game in games:
        if game.get("home_team") and game.get("away_team"):
            game_data.append({
                "game_id": game.get("id"),
                "season": game.get("season"),
                "week": game.get("week"),
                "neutral_site": game.get("neutral_site"),
                "conference_game": game.get("conference_game"),
                "attendance": game.get("attendance"),
                "home_team": game.get("home_team"),
                "home_team_id": game.get("home_id"),
                "home_conference": game.get("home_conference"),
                "home_points": game.get("home_points"),
                "away_team": game.get("away_team"),
                "away_team_id": game.get("away_id"),
                "away_conference": game.get("away_conference"),
                "away_points": game.get("away_points")
            })
    return pd.DataFrame(game_data)


def main():
    current_year = datetime.now().year
    start_year = 2015
    end_year = 2025

    for year in range(start_year, end_year):
        print(f"\n📅 Processing {year}...")
        year_dir = os.path.join(BASE_DIR, str(year))
        create_directory_if_not_exists(year_dir)

        for week in range(1, 20):  # You can raise to 20 if needed
            print(f"  📥 Week {week}...")

            week_file = os.path.join(year_dir, f"week{week}.csv")
            if os.path.exists(week_file):
                print(f"    ⏭️ Already exists, skipping.")
                continue

            games = fetch_games(year, week)
            if not games:
                print(f"    ⚠️ No games found.")
                pd.DataFrame().to_csv(week_file, index=False)
                continue

            df = process_games(games)
            df.to_csv(week_file, index=False)
            print(f"    ✅ Saved {len(df)} games to {week_file}")

            time.sleep(0.5)  # Politeness pause

if __name__ == "__main__":
    main()
