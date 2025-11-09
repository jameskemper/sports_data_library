import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --------------------------
# API Configuration
# --------------------------
API_KEY = os.getenv("CBBD_API_KEY")  # Loaded securely from GitHub Actions secret
API_URL = "https://api.collegebasketballdata.com/games"

if not API_KEY:
    raise ValueError("Missing API key. Make sure CBBD_API_KEY is set as a GitHub secret.")

headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# --------------------------
# Helper Functions
# --------------------------
def fetch_games(start_date, end_date):
    """Fetch games between two dates (inclusive)."""
    params = {
        "season": 2025,
        "startDateRange": start_date.isoformat(),
        "endDateRange": end_date.isoformat()
    }
    print(f"Fetching {start_date.date()} → {end_date.date()} ...")
    response = requests.get(API_URL, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    print(f" → {len(data)} games found")
    return data


def save_to_csv(df, output_path):
    """Save filtered DataFrame to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved {len(df)} games to {output_path}")


# --------------------------
# Main Script
# --------------------------
def main():
    print("Starting NCAA Basketball Schedule Fetch")

    start_of_season = datetime(2024, 11, 1)
    end_of_season = datetime(2025, 4, 15)
    delta = timedelta(days=30)

    all_games = []
    current_start = start_of_season

    # Loop through month-long ranges to bypass 3,000-game cap
    while current_start <= end_of_season:
        current_end = min(current_start + delta, end_of_season)
        try:
            games = fetch_games(current_start, current_end)
            all_games.extend(games)
        except Exception as e:
            print(f"Error fetching {current_start.date()} → {current_end.date()}: {e}")
        current_start = current_end + timedelta(days=1)
        time.sleep(0.25)  # avoid API rate limits

    print(f"\n Total games fetched: {len(all_games)}")

    # Convert to DataFrame and filter columns
    df = pd.DataFrame(all_games)
    keep_cols = [
        "id", "sourceId", "seasonLabel", "season", "seasonType", "tournament",
        "startDate", "startTimeTbd", "neutralSite", "conferenceGame", "gameType",
        "homeTeamId", "homeTeam", "homeConferenceId", "homeConference", "homeSeed",
        "awayTeamId", "awayTeam", "awayConferenceId", "awayConference", "awaySeed",
        "venueId", "venue", "city", "state"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    # Save to repo path
    output_path = "NCAA_basketball/schedule/2025.csv"
    save_to_csv(df, output_path)

    print("\Done! Schedule data updated successfully.")


if __name__ == "__main__":
    main()
