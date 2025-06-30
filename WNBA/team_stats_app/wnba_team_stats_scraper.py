import requests
import pandas as pd
import os
from datetime import datetime, timedelta
import time

# Dynamically set save path relative to script
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "data", "2025")
os.makedirs(save_path, exist_ok=True)

# Full browser-like headers
headers = {
    "Host": "stats.wnba.com",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.wnba.com/stats/",
    "Origin": "https://www.wnba.com",
}

# Get yesterday's date
yesterday = datetime.utcnow() - timedelta(days=1)
date_str = yesterday.strftime("%m/%d/%Y")
filename_date = yesterday.strftime("%m_%d_%Y")

print(f"📅 Processing {date_str}...")

url = "https://stats.wnba.com/stats/leaguedashteamstats"
params = {
    "Conference": "",
    "DateFrom": date_str,
    "DateTo": date_str,
    "Division": "",
    "GameScope": "",
    "GameSegment": "",
    "LastNGames": "0",
    "LeagueID": "10",
    "Location": "",
    "MeasureType": "Base",
    "Month": "0",
    "OpponentTeamID": "0",
    "Outcome": "",
    "PORound": "0",
    "PaceAdjust": "N",
    "PerMode": "PerGame",
    "Period": "0",
    "PlayerExperience": "",
    "PlayerPosition": "",
    "PlusMinus": "N",
    "Rank": "N",
    "Season": "2025",
    "SeasonType": "Regular Season",
    "ShotClockRange": "",
    "StarterBench": "",
    "TeamID": "0",
    "TwoWay": "0",
    "VsConference": "",
    "VsDivision": ""
}

retries = 3
for attempt in range(retries):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        break
    except Exception as e:
        print(f"⚠️ Attempt {attempt+1} failed: {e}")
        if attempt < retries - 1:
            time.sleep(5)
        else:
            print(f"❌ Skipping {date_str}")
            data = None

if data and data['resultSets'][0]['rowSet']:
    headers_ = data['resultSets'][0]['headers']
    rows = data['resultSets'][0]['rowSet']
    df = pd.DataFrame(rows, columns=headers_)
    df["date"] = date_str

    file_path = os.path.join(save_path, f"{filename_date}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved to {file_path}")
else:
    print(f"⚠️ No data found for {date_str}")
