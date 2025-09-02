import os
import requests
import json
from datetime import datetime

API_KEY = os.getenv("CFBD_API_KEY")
BASE_URL = "https://apinext.collegefootballdata.com/games"
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
DATA_DIR = "box_scores_app/data/weeks_2025"
WEEK = int(datetime.now().strftime("%U")) - 31  # Week number relative to August

def fetch_and_save_boxscores(year=2025, week=WEEK):
    print(f"Attempting to fetch week: {week}")
    
    if week < 1 or week > 15:
        print(f"Skipping invalid week: {week}")
        return
    
    if not API_KEY:
        print("Error: CFBD_API_KEY environment variable not set")
        return
        
    params = {
        "year": year,
        "week": week,
        "seasonType": "regular",
        "classification": "fbs"
    }
    
    response = requests.get(BASE_URL, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        data = response.json()
        os.makedirs(DATA_DIR, exist_ok=True)
        file_path = os.path.join(DATA_DIR, f"week_{week:02d}.json")
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved week {week} to {file_path}")
    else:
        print(f"Failed to fetch data for week {week}: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    fetch_and_save_boxscores()