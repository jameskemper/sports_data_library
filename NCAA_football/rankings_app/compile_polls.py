#!/usr/bin/env python3
import os
import json
import pandas as pd

YEAR = int(os.getenv("YEAR", 2025))
LAST_WEEK = 16

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"weekly_rankings_{YEAR}.csv")
FLAG_FILE = os.path.join(BASE_DIR, "polls_changed.flag")

def compile_all():
    rows = []
    for week in range(1, LAST_WEEK + 1):
        fname = os.path.join(WEEKS_DIR, f"week_{week:02}.json")
        if not os.path.exists(fname):
            print(f"❌ Week {week}: {fname} not found")
            continue

        print(f"📂 Processing {fname}")
        with open(fname, "r") as f:
            week_data = json.load(f)

        if not isinstance(week_data, list):
            print(f"⚠️ Week {week}: unexpected format, skipping.")
            continue

        for poll in week_data:
            for ranking in poll.get("ranks", []):
                rows.append({
                    "season": poll.get("season", YEAR),
                    "week": poll.get("week", week),
                    "seasonType": poll.get("seasonType", "regular"),
                    "poll": poll.get("poll", "Unknown"),
                    "rank": ranking.get("rank"),
                    "school": ranking.get("school"),
                    "conference": ranking.get("conference", ""),
                    "firstPlaceVotes": ranking.get("firstPlaceVotes"),
                    "points": ranking.get("points")
                })

    return pd.DataFrame(rows)

def main():
    df = compile_all()
    if df.empty:
        print("❌ No poll data compiled.")
        return

    cols = [
        "season", "week", "seasonType", "poll", "rank",
        "school", "conference", "firstPlaceVotes", "points"
    ]
    df = df[cols].sort_values(["week", "poll", "rank"]).reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Rebuilt {OUTPUT_FILE} with {len(df)} rows.")

    with open(FLAG_FILE, "w") as f:
        f.write("true")

if __name__ == "__main__":
    main()
