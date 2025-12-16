import os
import json
import pandas as pd
from datetime import datetime

# =====================================================
# REPO-RELATIVE PATHS
# =====================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

RAW_DIR = os.path.join(
    REPO_ROOT,
    "NCAAW_basketball",
    "box_scores",
    "2025"
)

OUTPUT_CSV = os.path.join(
    REPO_ROOT,
    "NCAAW_basketball",
    "box_scores",
    "2025.csv"
)

# =====================================================
# HELPERS
# =====================================================
def flatten_prefixed(d, prefix):
    if not isinstance(d, dict):
        return {}
    return {f"{prefix}{k}": v for k, v in d.items() if k != "__typename"}

def date_from_filename(fname):
    d = datetime.strptime(fname[:8], "%m%d%Y")
    return d.strftime("%Y-%m-%d")

def season_from_date(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.year + 1 if d.month >= 7 else d.year

# =====================================================
# MAIN
# =====================================================
def main():
    rows = []
    files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith("_raw.jsonl"))

    print(f"Found {len(files)} raw JSONL files")

    for fname in files:
        game_date = date_from_filename(fname)
        season = season_from_date(game_date)

        with open(os.path.join(RAW_DIR, fname), "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                box = obj["boxscore"]
                gid = obj["game_id"]

                # Build team lookup
                team_lookup = {
                    str(t["teamId"]): {
                        "team": t.get("nameShort"),
                        "isHome": t.get("isHome")
                    }
                    for t in box.get("teams", [])
                }

                team_boxes = box.get("teamBoxscore", [])
                if len(team_boxes) != 2:
                    continue

                a, b = team_boxes

                def build_row(team, opp):
                    tid = str(team["teamId"])
                    oid = str(opp["teamId"])

                    return {
                        "gameId": gid,
                        "date": game_date,
                        "season": season,
                        "teamId": tid,
                        "team": team_lookup[tid]["team"],
                        "isHome": team_lookup[tid]["isHome"],
                        "opponentId": oid,
                        "opponent": team_lookup[oid]["team"],
                        **flatten_prefixed(team.get("teamStats"), "team_"),
                        **flatten_prefixed(opp.get("teamStats"), "opp_"),
                    }

                rows.append(build_row(a, b))
                rows.append(build_row(b, a))

    df = pd.DataFrame(rows)

    front = [
        "gameId", "date", "season",
        "teamId", "team", "isHome",
        "opponentId", "opponent",
        "team_points", "opp_points"
    ]

    df = df[[c for c in front if c in df.columns] +
            [c for c in df.columns if c not in front]]

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved compiled CSV → {OUTPUT_CSV}")
    print(f"Rows: {len(df):,}")

if __name__ == "__main__":
    main()
