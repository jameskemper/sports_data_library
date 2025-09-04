#!/usr/bin/env python3
"""
compile_box_scores_season.py

Reads weekly JSONs from data/weeks_<YEAR>/ and writes CSV:
data/boxscores_<YEAR>.csv
"""

import os
import json
import pandas as pd
from pathlib import Path

def compile_season():
    SCRIPT_DIR = Path(__file__).resolve().parent
    YEAR = int(os.getenv("YEAR", "2025"))

    INPUT_DIR = SCRIPT_DIR / "data" / f"weeks_{YEAR}"
    OUTPUT_PATH = SCRIPT_DIR / "data" / f"boxscores_{YEAR}.csv"

    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"No input dir: {INPUT_DIR}")

    frames = []
    for file in sorted(INPUT_DIR.glob("week_*.json")):
        with file.open("r", encoding="utf-8") as f:
            obj = json.load(f)

        meta = obj.get("_meta", {})
        data = obj.get("data", [])

        if not data:
            continue

        try:
            df = pd.json_normalize(data)
        except Exception:
            df = pd.DataFrame(data if isinstance(data, list) else [data])

        df["meta.year"] = meta.get("year", YEAR)
        df["meta.week"] = meta.get("week")
        df["meta.source_url"] = meta.get("source_url")
        frames.append(df)

    if not frames:
        print(f"No data rows found in {INPUT_DIR}")
        return

    season_df = pd.concat(frames, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    season_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(season_df)} rows → {OUTPUT_PATH}")

if __name__ == "__main__":
    compile_season()
