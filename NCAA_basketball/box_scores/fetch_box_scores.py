import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --------------------------
# API Configuration
# --------------------------
API_KEY = os.getenv("CBBD_API_KEY")
API_URL = "https://api.collegebasketballdata.com/games/teams"

headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# --------------------------
# Helper Functions
# --------------------------
def fetch_box_scores(season, start_date, end_date):
    """Fetch team box scores for a given season and date range."""
    params = {
        "season": season,
        "startDateRange": start_date.isoformat(),
        "endDateRange": end_date.isoformat()
    }
    print(f"Fetching {season}: {start_date.date()} → {end_date.date()} ...")
    try:
        response = requests.get(API_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"Retrieved {len(data)} box scores")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {season} ({start_date.date()} → {end_date.date()}): {e}")
        return []

def flatten_stats(df):
    """Flatten teamStats and opponentStats JSON columns."""
    if "teamStats" not in df.columns or "opponentStats" not in df.columns:
        print("No nested stats to flatten.")
        return df

    team_stats = pd.json_normalize(df["teamStats"])
    opp_stats = pd.json_normalize(df["opponentStats"])

    team_stats.columns = [f"team_{col}" for col in team_stats.columns]
    opp_stats.columns = [f"opp_{col}" for col in opp_stats.columns]

    df = pd.concat([df.drop(columns=["teamStats", "opponentStats"]),
                    team_stats, opp_stats], axis=1)
    return df

# --------------------------
# Main Script
# --------------------------
def main():
    season = 2026
    start_of_season = datetime(2025, 11, 1)
    end_of_season = datetime(2026, 4, 15)
    delta = timedelta(days=30)

    all_games = []
    current_start = start_of_season

    while current_start <= end_of_season:
        current_end = min(current_start + delta, end_of_season)
        games = fetch_box_scores(season, current_start, current_end)
        all_games.extend(games)
        current_start = current_end + timedelta(days=1)
        time.sleep(0.25)

    if not all_games:
        print("No box score data retrieved. Exiting.")
        return

    df = pd.DataFrame(all_games)
    df = flatten_stats(df)

    # Reorder columns
    front_cols = [
        "gameId", "season", "seasonType", "startDate", "home",
        "team", "conference", "opponent", "opponentConference",
        "team_points", "opp_points"
    ]
    df = df[[c for c in front_cols if c in df.columns] +
            [c for c in df.columns if c not in front_cols]]

    output_path = "NCAA_basketball/box_scores/2026.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved flattened box scores to: {output_path}")

if __name__ == "__main__":
    main()
