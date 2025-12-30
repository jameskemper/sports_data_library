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

def transform_to_boxscore_format(games_data):
    """
    Transform API response to match boxscore variable structure.
    Creates two rows per game (one from each team's perspective).
    """
    rows = []
    
    for game in games_data:
        # Create home team row
        home_row = {
            'gameid': game.get('id'),
            'season': game.get('season'),
            'seasontype': game.get('seasonType'),
            'startdate': game.get('startDate'),
            'team': game.get('homeTeam'),
            'conference': game.get('homeConference'),
            'opponent': game.get('awayTeam'),
            'opponentconference': game.get('awayConference'),
            'seasonlabel': game.get('seasonLabel'),
            'tournament': game.get('tournament'),
            'starttimetbd': game.get('startTimeTbd'),
            'teamid': game.get('homeTeamId'),
            'teamseed': game.get('homeSeed'),
            'opponentid': game.get('awayTeamId'),
            'opponentseed': game.get('awaySeed'),
            'neutralsite': game.get('neutralSite'),
            'ishome': True,
            'conferencegame': game.get('conferenceGame'),
            'gametype': game.get('gameType'),
            'notes': None  # Not in API response
        }
        rows.append(home_row)
        
        # Create away team row
        away_row = {
            'gameid': game.get('id'),
            'season': game.get('season'),
            'seasontype': game.get('seasonType'),
            'startdate': game.get('startDate'),
            'team': game.get('awayTeam'),
            'conference': game.get('awayConference'),
            'opponent': game.get('homeTeam'),
            'opponentconference': game.get('homeConference'),
            'seasonlabel': game.get('seasonLabel'),
            'tournament': game.get('tournament'),
            'starttimetbd': game.get('startTimeTbd'),
            'teamid': game.get('awayTeamId'),
            'teamseed': game.get('awaySeed'),
            'opponentid': game.get('homeTeamId'),
            'opponentseed': game.get('homeSeed'),
            'neutralsite': game.get('neutralSite'),
            'ishome': False,
            'conferencegame': game.get('conferenceGame'),
            'gametype': game.get('gameType'),
            'notes': None  # Not in API response
        }
        rows.append(away_row)
    
    return pd.DataFrame(rows)

def save_to_csv(df, output_path):
    """Save filtered DataFrame to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved {len(df)} rows ({len(df)//2} games) to {output_path}")

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
    
    print(f"\n📊 Total games fetched: {len(all_games)}")
    
    # Transform to boxscore format
    df = transform_to_boxscore_format(all_games)
    
    # Ensure column order matches boxscore structure (schedule columns only)
    column_order = [
        'gameid', 'season', 'seasontype', 'startdate', 'team', 'conference',
        'opponent', 'opponentconference', 'seasonlabel', 'tournament',
        'starttimetbd', 'teamid', 'teamseed', 'opponentid', 'opponentseed',
        'neutralsite', 'ishome', 'conferencegame', 'gametype', 'notes'
    ]
    
    df = df[column_order]
    
    # Save to repo path
    output_path = "NCAA_basketball/schedule/2025.csv"
    save_to_csv(df, output_path)
    
    print("\n✅ Done! Schedule data updated successfully.")
    print(f"   Format: Each game creates 2 rows (home & away team perspectives)")

if __name__ == "__main__":
    main()
