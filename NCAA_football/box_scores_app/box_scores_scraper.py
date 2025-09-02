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
WEEK = int(datetime.now().strftime("%U")) - 31

def fetch_and_save_boxscores(year=2025, week=WEEK):
    print(f"Starting fetch for year: {year}, week: {week}")
    print(f"API Key present: {bool(API_KEY)}")
    
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
    
    print(f"Making request to: {BASE_URL}")
    print(f"With params: {params}")
    
    response = requests.get(BASE_URL, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Received {len(data)} games")
        
        # Create directory and show full path
        os.makedirs(DATA_DIR, exist_ok=True)
        file_path = os.path.join(DATA_DIR, f"week_{week:02d}.json")
        full_path = os.path.abspath(file_path)
        
        print(f"Saving to: {full_path}")
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
            
        # Verify file was created
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✓ File saved successfully: {file_size} bytes")
        else:
            print("✗ File was not created!")
            
    else:
        print(f"Failed to fetch data for week {week}: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    fetch_and_save_boxscores()
