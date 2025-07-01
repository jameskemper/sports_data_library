import requests
import pandas as pd
import os
from datetime import datetime, timedelta

# -------------------------------
# Setup paths
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "data", "2025")
os.makedirs(save_path, exist_ok=True)

# -------------------------------
# Yesterday's date
# -------------------------------
yesterday = datetime.now() - timedelta(days=1)
date_str = yesterday.strftime("%Y%m%d")       # ESPN format
filename_date = yesterday.strftime("%m_%d_%Y")

print(f"📅 Collecting player stats for games on {date_str}...")

# -------------------------------
# Get scoreboard to find games
# -------------------------------
scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_str}"
resp = requests.get(scoreboard_url, timeout=30)
resp.raise_for_status()
scoreboard = resp.json()
game_ids = [event['id'] for event in scoreboard.get('events', [])]

if not game_ids:
    print(f"⚠️ No games found for {date_str}.")
    exit()

print(f"✅ Found {len(game_ids)} games.")

# -------------------------------
# Collect player-level stats
# -------------------------------
all_player_stats = []

for i, game_id in enumerate(game_ids, 1):
    print(f"📦 Fetching summary for GameID {game_id} ({i}/{len(game_ids)})...")
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={game_id}"
    resp = requests.get(summary_url, timeout=30)
    resp.raise_for_status()
    summary = resp.json()

    try:
        players_section = summary['boxscore']['players']
        for team_data in players_section:
            team_name = team_data['team']['shortDisplayName']
            stats_info = team_data.get('statistics', [])[0]
            stat_keys = stats_info['keys']  # like ["minutes", "fieldGoalsMade-fieldGoalsAttempted", ...]

            for athlete in stats_info['athletes']:
                if athlete.get('didNotPlay'):
                    continue  # skip players who did not play

                player_info = athlete['athlete']
                stats_line = athlete.get('stats', [])
                
                player_record = {
                    'GameID': game_id,
                    'Date': date_str,
                    'Team': team_name,
                    'PlayerID': player_info.get('id'),
                    'Player': player_info.get('displayName'),
                    'Position': player_info.get('position', {}).get('abbreviation'),
                    'Jersey': player_info.get('jersey')
                }

                # map stats keys to actual values
                for key, value in zip(stat_keys, stats_line):
                    player_record[key] = value

                all_player_stats.append(player_record)
    except Exception as e:
        print(f"⚠️ No player stats structure found for team {team_name} in GameID {game_id}: {e}")

# -------------------------------
# Save DataFrame
# -------------------------------
if all_player_stats:
    df = pd.DataFrame(all_player_stats)

    # preferred order
    preferred_cols = [
        'GameID', 'Date', 'Team', 'PlayerID', 'Player', 'Position', 'Jersey',
        'minutes', 'fieldGoalsMade-fieldGoalsAttempted', 'threePointFieldGoalsMade-threePointFieldGoalsAttempted',
        'freeThrowsMade-freeThrowsAttempted', 'offensiveRebounds', 'defensiveRebounds', 'rebounds',
        'assists', 'steals', 'blocks', 'turnovers', 'fouls', 'plusMinus', 'points'
    ]
    existing_cols = [c for c in preferred_cols if c in df.columns]
    df = df[existing_cols + [c for c in df.columns if c not in existing_cols]]

    file_path = os.path.join(save_path, f"{filename_date}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved {len(df)} player rows to {file_path}")
else:
    print(f"⚠️ No player stats collected for {date_str}.")
