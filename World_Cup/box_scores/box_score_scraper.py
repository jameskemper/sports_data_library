import os
import json
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =====================================================
# 2026 FIFA WORLD CUP BOX SCORE SCRAPER (ESPN API)
# Runs hourly via GitHub Actions. Each run re-scrapes
# yesterday and today (US/Eastern) and rewrites those
# daily raw JSONL files with all COMPLETED matches.
# One summary call per game contains both team and
# player stats; compilers build the CSVs from the raw.
# =====================================================

# REPO-RELATIVE PATHS
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR = os.path.join(REPO_ROOT, "World_Cup", "box_scores", "2026")
os.makedirs(OUT_DIR, exist_ok=True)

# API CONFIG
LEAGUE = "fifa.world"
BASE_URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{LEAGUE}"
REQUEST_TIMEOUT = 30
SLEEP_SECONDS = 1.0

# TOURNAMENT WINDOW (group stage Jun 11 - final Jul 19, 2026;
# scrape through Jul 21 to pick up late corrections)
TOURNEY_START = datetime(2026, 6, 11).date()
TOURNEY_END   = datetime(2026, 7, 21).date()

EASTERN = ZoneInfo("America/New_York")


def get_json(url: str) -> dict:
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def scoreboard_url(d: datetime) -> str:
    return f"{BASE_URL}/scoreboard?dates={d:%Y%m%d}"


def summary_url(game_id: str) -> str:
    return f"{BASE_URL}/summary?event={game_id}"


def trim_summary(game_id: str, event: dict, summary: dict) -> dict:
    """Keep only what the compilers need; full summaries are ~0.5MB each
    (commentary, odds, etc.) and would bloat the repo."""
    comp = (event.get("competitions") or [{}])[0]
    return {
        "game_id": game_id,
        "name": event.get("name"),
        "shortName": event.get("shortName"),
        "date": event.get("date"),
        "stage": (event.get("season") or {}).get("slug"),
        "venue": (comp.get("venue") or {}).get("fullName"),
        "city": ((comp.get("venue") or {}).get("address") or {}).get("city"),
        "country": ((comp.get("venue") or {}).get("address") or {}).get("country"),
        "attendance": comp.get("attendance"),
        "status": ((comp.get("status") or {}).get("type") or {}).get("detail"),
        "competitors": [
            {
                "teamId": c.get("id"),
                "homeAway": c.get("homeAway"),
                "winner": c.get("winner"),
                "score": c.get("score"),
                "shootoutScore": c.get("shootoutScore"),
                "team": {
                    "id": (c.get("team") or {}).get("id"),
                    "abbreviation": (c.get("team") or {}).get("abbreviation"),
                    "displayName": (c.get("team") or {}).get("displayName"),
                },
            }
            for c in comp.get("competitors", [])
        ],
        "boxscore_teams": (summary.get("boxscore") or {}).get("teams", []),
        "rosters": summary.get("rosters", []),
    }


def scrape_date(d: datetime):
    date_tag = d.strftime("%m%d%Y")
    out_path = os.path.join(OUT_DIR, f"{date_tag}_raw.jsonl")

    sb_url = scoreboard_url(d)
    print(f"\n=== {d:%Y-%m-%d} ===")
    print(f"Scoreboard: {sb_url}")
    try:
        sb = get_json(sb_url)
    except requests.RequestException as e:
        print(f"Scoreboard fetch failed: {e}")
        return

    events = sb.get("events", [])
    completed = [
        e for e in events
        if ((e.get("status") or {}).get("type") or {}).get("completed")
    ]
    print(f"Found {len(events)} games, {len(completed)} completed")
    if not completed:
        print("No completed games yet — skipping file write.")
        return

    records = []
    for i, event in enumerate(completed, 1):
        gid = event["id"]
        try:
            summary = get_json(summary_url(gid))
            records.append(trim_summary(gid, event, summary))
            print(f"[{i}/{len(completed)}] {event.get('shortName')} OK")
        except requests.RequestException as e:
            print(f"[{i}/{len(completed)}] ERROR {gid}: {e}")
        time.sleep(SLEEP_SECONDS)

    if not records:
        return

    # Rewrite the daily file each run so newly completed games are added
    # and any stat corrections are picked up.
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Saved {len(records)} games -> {out_path}")


def main():
    now_et = datetime.now(EASTERN)
    if not (TOURNEY_START <= now_et.date() <= TOURNEY_END):
        print(f"{now_et.date()} is outside the tournament window. Nothing to do.")
        return

    # Yesterday first (late kickoffs finish after midnight ET), then today.
    for d in [now_et - timedelta(days=1), now_et]:
        if TOURNEY_START <= d.date() <= TOURNEY_END:
            scrape_date(d)
    print("\nDone.")


if __name__ == "__main__":
    main()
