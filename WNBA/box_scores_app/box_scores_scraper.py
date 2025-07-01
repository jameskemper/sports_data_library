import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from pytz import timezone  # ✅ NEW

# -------------------------------
# Setup paths
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "data", "2025")
os.makedirs(save_path, exist_ok=True)

# -------------------------------
# Yesterday's date in US Central
# -------------------------------
central = timezone('US/Central')                # ✅ NEW
now_central = datetime.now(central)             # ✅ NEW
yesterday = now_central - timedelta(days=1)     # ✅ MODIFIED
date_str = yesterday.strftime("%Y%m%d")         # ESPN format
filename_date = yesterday.strftime("%m_%d_%Y")

print(f"📅 Collecting ESPN WNBA box scores for games on {date_str}...")

# -------------------------------
# Get scoreboard from ESPN
# -------------------------------
scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"
resp = requests.get(scoreboard_url, timeout=30)
resp.raise_for_status()
scoreboard = resp.json()

# -------------------------------
# Extract game IDs
# -------------------------------
game_ids = [event['id'] for event in scoreboard.get('events', [])]

if not game_ids:
    print(f"⚠️ No games found for {date_str}.")
else:
    print(f"✅ Found {len(game_ids)} games.")

# -------------------------------
# Fetch box scores for each game
# -------------------------------
all_team_stats = []

for i, game_id in enumerate(game_ids, 1):
    print(f"📦 Fetching box score for ESPN GameID {game_id} ({i}/{len(game_ids)})...")
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={game_id}"
    resp = requests.get(summary_url, timeout=30)
    resp.raise_for_status()
    summary = resp.json()

    try:
        teams = summary['boxscore']['teams']
        for team in teams:
            stats_flat = {
                'GameID': game_id,
                'Date': date_str,
                'TeamName': team['team']['shortDisplayName']
            }
            for stat in team['statistics']:
                stats_flat[stat['name']] = stat['displayValue']
            all_team_stats.append(stats_flat)
    except Exception as e:
        print(f"⚠️ Failed to extract team stats for GameID {game_id}: {e}")

# -------------------------------
# Build DataFrame
# -------------------------------
if all_team_stats:
    df = pd.DataFrame(all_team_stats)

    # -------------------------------
    # Clean: split FGM/FGA, 3PM/3PA, FTM/FTA
    # -------------------------------
    if 'fieldGoalsMade-fieldGoalsAttempted' in df.columns:
        df[['FGM', 'FGA']] = df['fieldGoalsMade-fieldGoalsAttempted'].str.split('-', expand=True).astype(int)
    if 'threePointFieldGoalsMade-threePointFieldGoalsAttempted' in df.columns:
        df[['3PM', '3PA']] = df['threePointFieldGoalsMade-threePointFieldGoalsAttempted'].str.split('-', expand=True).astype(int)
    if 'freeThrowsMade-freeThrowsAttempted' in df.columns:
        df[['FTM', 'FTA']] = df['freeThrowsMade-freeThrowsAttempted'].str.split('-', expand=True).astype(int)

    # Drop original compact columns
    df.drop(columns=[
        c for c in [
            'fieldGoalsMade-fieldGoalsAttempted',
            'threePointFieldGoalsMade-threePointFieldGoalsAttempted',
            'freeThrowsMade-freeThrowsAttempted'
        ] if c in df.columns
    ], inplace=True)

    # -------------------------------
    # Reorder columns
    # -------------------------------
    preferred_cols = [
        'GameID', 'Date', 'TeamName', 'FGM', 'FGA', 'fieldGoalPct',
        '3PM', '3PA', 'threePointFieldGoalPct',
        'FTM', 'FTA', 'freeThrowPct',
        'totalRebounds', 'offensiveRebounds', 'defensiveRebounds',
        'assists', 'steals', 'blocks', 'turnovers',
        'personalFouls', 'points', 'fastBreakPoints',
        'pointsInPaint', 'largestLead'
    ]
    existing_cols = [col for col in preferred_cols if col in df.columns]
    df = df[existing_cols + [c for c in df.columns if c not in existing_cols]]

    # -------------------------------
    # Save cleaned CSV
    # -------------------------------
    file_path = os.path.join(save_path, f"{filename_date}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved {len(df)} rows to {file_path}")
else:
    print(f"⚠️ No box score data collected.")