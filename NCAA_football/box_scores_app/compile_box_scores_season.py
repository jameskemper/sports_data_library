#!/usr/bin/env python3
"""
compile_box_scores_season.py

Compiles weekly CFBD game JSONs into a clean season CSV.
Matches 2024 format, using correct camelCase keys from API.
"""

import os
import json
import pandas as pd
from pathlib import Path

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
        "season_type": game.get("seasonType"),     # fixed
        "start_date": game.get("startDate"),       # fixed
        "completed": game.get("completed"),
        "neutral_site": game.get("neutralSite"),   # fixed
        "conference_game": game.get("conferenceGame"),  # fixed
        "venue_id": game.get("venueId"),           # fixed
        "venue": game.get("venue"),
        "home_id": game.get("homeId"),             # fixed
        "home_team": game.get("homeTeam"),         # fixed
        "home_conference": game.get("homeConference"),  # fixed
        "home_points": game.get("homePoints"),     # fixed
        "away_id": game.get("awayId"),             # fixed
        "away_team": game.get("awayTeam"),         # fixed
        "away_conference": game.get("awayConference"),  # fixed
        "away_points": game.get("awayPoints"),     # fixed
    }

def compile_season():
    SCRIPT_DIR = Path(__file__).resolve().parent
    YEAR = int(os.getenv("YEAR", "2025"))

    INPUT_DIR = SCRIPT_DIR / "data" / f"weeks_{YEAR}"
    OUTPUT_PATH = SCRIPT_DIR / "data" / f"box_scores_{YEAR}.csv"

    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"No input dir: {INPUT_DIR}")

    rows = []
    for file in sorted(INPUT_DIR.glob("week_*.json")):
        with file.open("r", encoding="utf-8") as f:
            obj = json.load(f)

        games = obj.get("data", [])
        if not isinstance(games, list):
            continue

        for g in games:
            rows.append(extract_game_fields(g))

    if not rows:
        print(f"No data found in {INPUT_DIR}")
        return

    df = pd.DataFrame(rows, columns=KEEP_COLS)

    # ✅ Deduplicate by game id
    if "id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["id"], keep="last")
        after = len(df)
        if before != after:
            print(f"Deduplicated {before - after} duplicate games")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows → {OUTPUT_PATH}")

if __name__ == "__main__":
    compile_season()
