import os
import json
import pandas as pd

# =====================================================
# 2026 FIFA WORLD CUP PLAYER BOX SCORE COMPILER
# Reads the same daily raw JSONL files written by
# World_Cup/box_scores/box_score_scraper.py and builds
# one row per player per match from ESPN rosters.
# =====================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RAW_DIR = os.path.join(REPO_ROOT, "World_Cup", "box_scores", "2026")
OUTPUT_CSV = os.path.join(REPO_ROOT, "World_Cup", "player_box_scores", "2026.csv")

SEASON = 2026


def sub_flag(v) -> bool:
    """subbedIn/subbedOut can be bool or dict like {'didSub': True, ...}."""
    if isinstance(v, dict):
        return bool(v.get("didSub"))
    return bool(v)


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"No raw directory found: {RAW_DIR}")
        return

    rows = []
    files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith("_raw.jsonl"))
    print(f"Found {len(files)} raw JSONL files")

    for fname in files:
        with open(os.path.join(RAW_DIR, fname), "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)

                # Opponent lookup from competitors
                comps = rec.get("competitors", [])
                names_by_id = {
                    str((c.get("team") or {}).get("id")):
                        (c.get("team") or {}).get("displayName")
                    for c in comps
                }

                for side in rec.get("rosters", []):
                    team = side.get("team") or {}
                    tid = str(team.get("id"))
                    opp_ids = [i for i in names_by_id if i != tid]
                    oid = opp_ids[0] if opp_ids else None

                    for pl in side.get("roster", []):
                        ath = pl.get("athlete") or {}
                        row = {
                            "gameId": rec.get("game_id"),
                            "date": (rec.get("date") or "")[:10],
                            "season": SEASON,
                            "stage": rec.get("stage"),
                            "teamId": tid,
                            "team": team.get("displayName"),
                            "isHome": side.get("homeAway") == "home",
                            "opponentId": oid,
                            "opponent": names_by_id.get(oid),
                            "playerId": ath.get("id"),
                            "player": ath.get("displayName"),
                            "jersey": pl.get("jersey"),
                            "position": (pl.get("position") or {}).get("abbreviation"),
                            "starter": pl.get("starter"),
                            "subbedIn": sub_flag(pl.get("subbedIn")),
                            "subbedOut": sub_flag(pl.get("subbedOut")),
                            "formationPlace": pl.get("formationPlace"),
                        }
                        for s in pl.get("stats", []):
                            name = s.get("name")
                            if name:
                                row[name] = s.get("value", s.get("displayValue"))
                        rows.append(row)

    if not rows:
        print("No player box scores compiled yet.")
        return

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["gameId", "playerId"], keep="last", inplace=True)
    df.sort_values(["date", "gameId", "teamId"], inplace=True)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved compiled player box scores -> {OUTPUT_CSV}")
    print(f"Rows: {len(df):,}")


if __name__ == "__main__":
    main()
