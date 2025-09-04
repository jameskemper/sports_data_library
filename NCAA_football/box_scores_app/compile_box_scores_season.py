#!/usr/bin/env python3
"""
compile_box_scores_season.py

Compiles weekly CFBD game/box score JSONs into a clean season CSV.
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

def safe_val(obj, key=None):
    """
    Safely extract from CFBD JSON fields that might be dict, str, or None.
    - If obj is dict and key is given → return obj.get(key)
    - If obj is dict and no key → return None
    - If obj is str → return obj (only if no key)
    - Else → None
    """
    if isinstance(obj, dict):
        return obj.get(key) if key else None
    if isinstance(obj, str) and key is None:
        return obj
    return None

def extract_game_fields(game: dict) -> dict:
    """Flatten one game dict into a row with selected fields."""
    return {
        "id": game.get("id"),
        "season": game.get("season"),
        "week": game.get("week"),
        "season_type": game.get("season_type"),
        "start_date": game.get("start_date"),
        "completed": game.get("completed"),
        "neutral_site": game.get("neutral_site"),
        "conference_game": game.get("conference_game"),
        "venue_id": safe_val(game.get("venue"), "id"),
        "venue": safe_val(game.get("venue"), "name") or safe_val(game.get("venue")),
        "home_id": safe_val(game.get("home_team"), "id"),
        "home_team": safe_val(game.get("home_team"), "school") or game.get("home_team"),
        "home_conference": safe_val(game.get("home_team"), "conference"),
        "home_points": game.get("home_points"),
        "away_id": safe_val(game.get("away_team"), "id"),
        "away_team": safe_val(game.get("away_team"), "school") or game.get("away_team"),
        "away_conference": safe_val(game.get("away_team"), "conference"),
        "away_points": game.get("away_points"),
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
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows → {OUTPUT_PATH}")

if __name__ == "__main__":
    compile_season()
