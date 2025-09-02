#!/usr/bin/env python3
"""
compile_box_scores_season.py

Reads weekly JSONs from data/weeks_<YEAR>/ and writes a compiled CSV:
data/boxscores_<YEAR>.csv

The scraper writes JSON as:
  {"_meta": {...}, "data": <list|dict|...>}

This compiler:
- Loads each week_XX.json
- Extracts the "data" field if present; otherwise uses the whole JSON
- Normalizes to a DataFrame (json_normalize)
- Adds 'year' and 'week' from _meta if available (fallback: infer week from filename)
- Concats and writes CSV
"""

import os
import re
import json
import pandas as pd
from pathlib import Path

def compile_season():
    SCRIPT_DIR = Path(__file__).resolve().parent
    YEAR = int(os.getenv("YEAR", "2025"))

    INPUT_DIR = SCRIPT_DIR / "data" / f"weeks_{YEAR}"
    OUTPUT_PATH = SCRIPT_DIR / "data" / f"boxscores_{YEAR}.csv"

    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input dir not found: {INPUT_DIR}")

    frames = []

    week_re = re.compile(r"week_(\d{2})\.json$", re.IGNORECASE)

    for file in sorted(INPUT_DIR.glob("week_*.json")):
        week = None
        m = week_re.search(file.name)
        if m:
            week = int(m.group(1))

        try:
            with file.open("r", encoding="utf-8") as f:
                obj = json.load(f)
        except Exception as e:
            print(f"Warn: failed to parse {file}: {e}")
            continue

        # Pull meta if present
        meta = obj.get("_meta", {}) if isinstance(obj, dict) else {}
        year = meta.get("year", YEAR)
        week_from_meta = meta.get("week", week)
        if week_from_meta is not None:
            week = week_from_meta

        # Extract data payload
        payload = obj.get("data", obj)
        # Normalize to DataFrame
        if isinstance(payload, list):
            if not payload:
                # Empty list -> still write a row with meta so the CSV is complete
                df = pd.DataFrame([{}])
            else:
                df = pd.json_normalize(payload, max_level=2)
        elif isinstance(payload, dict):
            df = pd.json_normalize(payload, max_level=2)
        else:
            # Fallback: wrap scalar/unknown as a single-row
            df = pd.DataFrame([{"value": payload}])

        # add meta columns
        df["meta.year"] = year
        df["meta.week"] = week
        df["meta.source_url"] = meta.get("source_url")
        df["meta.fetched_at_utc"] = meta.get("fetched_at_utc")
        df["meta.http_status"] = meta.get("http_status")
        df["meta.content_type"] = meta.get("content_type")

        frames.append(df)

    if not frames:
        print(f"No JSON files found in {INPUT_DIR}")
        return

    season_df = pd.concat(frames, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    season_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(season_df)} rows to {OUTPUT_PATH}")

if __name__ == "__main__":
    compile_season()
