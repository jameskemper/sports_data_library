import requests
import pandas as pd
import os
import time

# --------------------------
# API Configuration
# --------------------------
API_KEY = os.getenv("CBBD_API_KEY")
API_URL = "https://api.collegebasketballdata.com/rankings"

headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# --------------------------
# Helper Functions
# --------------------------
def fetch_weekly_rankings(season, week):
    params = {"season": season, "week": week}
    try:
        print(f"Fetching season {season}, week {week} ...")
        r = requests.get(API_URL, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        if not data:
            print(f"No data for {season} week {week}")
        else:
            print(f"Retrieved {len(data)} rows for {season} week {week}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {season} week {week}: {e}")
        return []

# --------------------------
# Main
# --------------------------
def main():
    season = 2026
    all_weeks = []
    week = 1

    while True:
        week_data = fetch_weekly_rankings(season, week)
        if not week_data:
            print(f"Completed fetching season {season}.")
            break
        for row in week_data:
            row["week"] = week
        all_weeks.extend(week_data)
        week += 1
        time.sleep(0.3)

    if not all_weeks:
        print(f"No data available for season {season}. Exiting.")
        return

    df = pd.DataFrame(all_weeks)
    keep_cols = [
        "season", "seasonType", "week", "pollDate", "pollType",
        "teamId", "team", "conference", "ranking", "points", "firstPlaceVotes"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    output_path = "NCAA_basketball/rankings/2026.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Rankings saved to {output_path}")

if __name__ == "__main__":
    main()
