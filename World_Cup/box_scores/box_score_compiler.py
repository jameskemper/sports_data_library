import os
import json
import pandas as pd

# =====================================================
# 2026 FIFA WORLD CUP TEAM BOX SCORE COMPILER
# Stacks all daily raw JSONL files into one CSV with
# two rows per match (one per team), each row carrying
# its own stats (team_) and the opponent's (opp_).
# =====================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RAW_DIR = os.path.join(REPO_ROOT, "World_Cup", "box_scores", "2026")
OUTPUT_CSV = os.path.join(REPO_ROOT, "World_Cup", "box_scores", "2026.csv")

SEASON = 2026


def stats_dict(team_box: dict, prefix: str) -> dict:
    """Flatten ESPN boxscore team statistics list into prefixed columns."""
    out = {}
    for s in team_box.get("statistics", []):
        name = s.get("name")
        if name:
            out[f"{prefix}{name}"] = s.get("displayValue")
    return out


def result_for(team: dict, opp: dict) -> str:
    if team.get("winner"):
        return "W"
    if opp.get("winner"):
        return "L"
    return "D"


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
                comps = rec.get("competitors", [])
                if len(comps) != 2:
                    continue

                # Map teamId -> boxscore stats block
                box_by_id = {
                    str((tb.get("team") or {}).get("id")): tb
                    for tb in rec.get("boxscore_teams", [])
                }

                a, b = comps

                def build_row(team, opp):
                    tid = str((team.get("team") or {}).get("id"))
                    oid = str((opp.get("team") or {}).get("id"))
                    row = {
                        "gameId": rec.get("game_id"),
                        "date": (rec.get("date") or "")[:10],
                        "season": SEASON,
                        "stage": rec.get("stage"),
                        "teamId": tid,
                        "team": (team.get("team") or {}).get("displayName"),
                        "teamAbbrev": (team.get("team") or {}).get("abbreviation"),
                        "isHome": team.get("homeAway") == "home",
                        "opponentId": oid,
                        "opponent": (opp.get("team") or {}).get("displayName"),
                        "team_score": team.get("score"),
                        "opp_score": opp.get("score"),
                        "team_shootout_score": team.get("shootoutScore"),
                        "opp_shootout_score": opp.get("shootoutScore"),
                        "result": result_for(team, opp),
                        "status": rec.get("status"),
                        "venue": rec.get("venue"),
                        "city": rec.get("city"),
                        "attendance": rec.get("attendance"),
                    }
                    row.update(stats_dict(box_by_id.get(tid, {}), "team_"))
                    row.update(stats_dict(box_by_id.get(oid, {}), "opp_"))
                    return row

                rows.append(build_row(a, b))
                rows.append(build_row(b, a))

    if not rows:
        print("No completed games compiled yet.")
        return

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["gameId", "teamId"], keep="last", inplace=True)
    df.sort_values(["date", "gameId", "isHome"], inplace=True)

    front = [
        "gameId", "date", "season", "stage",
        "teamId", "team", "teamAbbrev", "isHome",
        "opponentId", "opponent",
        "team_score", "opp_score", "result",
    ]
    df = df[[c for c in front if c in df.columns] +
            [c for c in df.columns if c not in front]]

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved compiled team box scores -> {OUTPUT_CSV}")
    print(f"Rows: {len(df):,}")


if __name__ == "__main__":
    main()
