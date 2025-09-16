#!/usr/bin/env python3
"""
compile_box_scores_backfill.py

Compiles weekly CFBD game JSONs into clean season CSVs.
Backfills 2010–2024 to match the 2025 schema.
"""

import json
import pandas as pd
from pathlib import Path

# Path to your data directory
BASE_DIR = Path(r"C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAA_football\box_scores_app\data")

KEEP_COLS = [
    "id",
    "season",
    "week",
    "season_type",
    "start_date",
    "completed",
    "neutral_site",
    "conference_game",
    "venue_id",
    "venue",
    "home_id",
    "home_team",
    "home_conference",
    "home_points",
    "away_id",
    "away_team",
    "away_conference",
    "away_points",
]

def extract_game_fields(game: dict) -> dict:
    """Flatten one game dict into a row with selected fields."""
    return {
        "id": game.get("id"),
        "season": game.get("season"),
        "week": game.get("week"),
        "season_type": game.get("seasonType"),
        "start_date": game.get("startDate"),
        "completed": game.get("completed"),
        "neutral_site": game.get("neutralSite"),
        "conference_game": game.get("conferenceGame"),
        "venue_id": game.get("venueId"),
        "venue": game.get("venue"),
        "home_id": game.get("homeId"),
        "home_team": game.get("homeTeam"),
        "home_conference": game.get("homeConference"),
        "home_points": game.get("homePoints"),
        "away_id": game.get("awayId"),
        "away_team": game.get("awayTeam"),
        "away_conference": game.get("awayConference"),
        "away_points": game.get("awayPoints"),
    }

def compile_season(year: int):
    input_dir = BASE_DIR / f"weeks_{year}"
    output_path = BASE_DIR / f"box_scores_{year}.csv"

    if not input_dir.exists():
        print(f"⚠️ Skipping {year} (no input dir: {input_dir})")
        return

    rows = []
    for file in sorted(input_dir.glob("week_*.json")):
        with file.open("r", encoding="utf-8") as f:
            obj = json.load(f)

        # Handle both dict-with-data and plain list
        if isinstance(obj, dict):
            games = obj.get("data", [])
        elif isinstance(obj, list):
            games = obj
        else:
            games = []

        if not isinstance(games, list):
            continue

        for g in games:
            rows.append(extract_game_fields(g))

    if not rows:
        print(f"⚠️ No data found for {year}")
        return

    df = pd.DataFrame(rows, columns=KEEP_COLS)

    # Deduplicate by game id
    if "id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["id"], keep="last")
        after = len(df)
        if before != after:
            print(f"🔄 {year}: Deduplicated {before - after} duplicate games")

    df.to_csv(output_path, index=False)
    print(f"✅ Wrote {len(df)} rows → {output_path}")

if __name__ == "__main__":
    for year in range(2010, 2025):  # 2010–2024
        compile_season(year)
