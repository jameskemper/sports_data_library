import requests
import pandas as pd
import os
from datetime import datetime, timedelta

# -------------------------------
# Setup paths
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "data", "2023")
os.makedirs(save_path, exist_ok=True)

# -------------------------------
# Loop through dates
# -------------------------------
start_date = datetime(2023, 6, 6)
end_date = datetime(2023, 10, 19)
delta = timedelta(days=1)

while start_date <= end_date:
    date_str = start_date.strftime("%Y%m%d")     # for ESPN URL
    filename_date = start_date.strftime("%m_%d_%Y")
    print(f"📅 Processing {date_str}...")

    # Check if already exists to skip
    out_file = os.path.join(save_path, f"{filename_date}.csv")
    if os.path.exists(out_file):
        print(f"✅ Already exists, skipping {out_file}")
        start_date += delta
        continue

    # -------------------------------
    # Get scoreboard from ESPN
    # -------------------------------
    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"
    try:
        resp = requests.get(scoreboard_url, timeout=30)
        resp.raise_for_status()
        scoreboard = resp.json()
    except Exception as e:
        print(f"⚠️ Failed to fetch scoreboard for {date_str}: {e}")
        start_date += delta
        continue

    # Extract game IDs
    game_ids = [event['id'] for event in scoreboard.get('events', [])]

    if not game_ids:
        print(f"⚠️ No games found for {date_str}.")
        start_date += delta
        continue

    print(f"✅ Found {len(game_ids)} games.")

    # -------------------------------
    # Fetch box scores for each game
    # -------------------------------
    all_team_stats = []

    for i, game_id in enumerate(game_ids, 1):
        print(f"📦 Fetching box score for ESPN GameID {game_id} ({i}/{len(game_ids)})...")
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={game_id}"
        try:
            resp = requests.get(summary_url, timeout=30)
            resp.raise_for_status()
            summary = resp.json()
        except Exception as e:
            print(f"⚠️ Failed to fetch box score for GameID {game_id}: {e}")
            continue

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
            print(f"⚠️ Failed to parse team stats for GameID {game_id}: {e}")

    # -------------------------------
    # Build DataFrame and clean
    # -------------------------------
    if all_team_stats:
        df = pd.DataFrame(all_team_stats)

        if 'fieldGoalsMade-fieldGoalsAttempted' in df.columns:
            df[['FGM', 'FGA']] = df['fieldGoalsMade-fieldGoalsAttempted'].str.split('-', expand=True).astype(int)
        if 'threePointFieldGoalsMade-threePointFieldGoalsAttempted' in df.columns:
            df[['3PM', '3PA']] = df['threePointFieldGoalsMade-threePointFieldGoalsAttempted'].str.split('-', expand=True).astype(int)
        if 'freeThrowsMade-freeThrowsAttempted' in df.columns:
            df[['FTM', 'FTA']] = df['freeThrowsMade-freeThrowsAttempted'].str.split('-', expand=True).astype(int)

        df.drop(columns=[
            c for c in [
                'fieldGoalsMade-fieldGoalsAttempted',
                'threePointFieldGoalsMade-threePointFieldGoalsAttempted',
                'freeThrowsMade-freeThrowsAttempted'
            ] if c in df.columns
        ], inplace=True)

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

        df.to_csv(out_file, index=False)
        print(f"✅ Saved {len(df)} rows to {out_file}")
    else:
        print(f"⚠️ No box score data collected for {date_str}.")

    # Move to next day
    start_date += delta
