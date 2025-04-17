import os
import requests
import pandas as pd
import time
from datetime import datetime

# --- API Details ---
API_KEY = 'zNmyTjCEh+r3C0Tg49VDiwiqo58mcIP6AwY12Cf9E981x0y0L+mEiwTRHrR0a3eN'
BASE_URL = 'https://api.collegefootballdata.com'
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "accept": "application/json"
}

# --- Directory to Save Rosters ---
BASE_DIR = r'C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAA_football\season_stats\rosters'

def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_fbs_teams():
    """
    Fetch the list of FBS teams.
    This endpoint returns data for every FBS team.
    """
    teams_url = f"{BASE_URL}/teams/fbs"
    try:
        response = requests.get(teams_url, headers=HEADERS)
        response.raise_for_status()
        teams = response.json()
        return teams
    except Exception as e:
        print(f"Error fetching FBS teams: {e}")
        return []

def get_roster_for_team(year, team_name):
    """
    Fetch roster for a team in a given year using the correct endpoint.
    """
    url = f"{BASE_URL}/roster"
    params = {
        "year": year,
        "team": team_name
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params)

        # Confirm we're getting JSON, not HTML
        if response.headers.get("Content-Type", "").startswith("text/html"):
            print(f"    ⚠️ HTML page received for {team_name} in {year}, likely wrong endpoint or bad format.")
            return []

        response.raise_for_status()
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"    JSON decode error for {team_name} in {year}. Response: {response.text[:100]}")
        return []
    except Exception as e:
        print(f"    ❌ Error fetching roster for {team_name} in {year}: {e}")
        return []



def main():
    # Create the base directory for roster CSV files if it doesn't exist.
    create_directory_if_not_exists(BASE_DIR)

    # Get the list of FBS teams (ideally includes a 'school' field).
    print("Fetching list of FBS teams...")
    teams_list = get_fbs_teams()
    if not teams_list:
        print("No teams found. Exiting.")
        return

    # Extract team names (using the 'school' key).
    team_names = [team.get("school") for team in teams_list if team.get("school")]
    print(f"Found {len(team_names)} teams.")

    # Define the range of years for which to fetch rosters.
    start_year = 2015
    end_year = 2025  # Adjust the end year as needed

    for year in range(start_year, end_year):
        print(f"\nFetching rosters for year {year}...")
        all_rosters = []
        for team in team_names:
            print(f"  Fetching roster for {team}...")
            roster = get_roster_for_team(year, team)
            if roster:
                all_rosters.extend(roster)
            else:
                print(f"    No roster data for {team} in {year}.")
            # Pause to avoid hitting API rate limits.
            time.sleep(0.5)

        # Save the combined roster data for the current year.
        if all_rosters:
            df_rosters = pd.DataFrame(all_rosters)
            file_path = os.path.join(BASE_DIR, f"rosters_{year}.csv")
            df_rosters.to_csv(file_path, index=False)
            print(f"  Saved rosters for year {year} with {len(df_rosters)} records to {file_path}.")
        else:
            print(f"  No roster data collected for year {year}.")

if __name__ == "__main__":
    main()
