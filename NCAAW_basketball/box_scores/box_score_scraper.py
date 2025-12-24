import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
# =====================================================
# REPO-RELATIVE PATHS (FIXED)
# =====================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR = os.path.join(
    REPO_ROOT,
    "NCAAW_basketball",
    "box_scores",
    "2026"
)
os.makedirs(OUT_DIR, exist_ok=True)
# =====================================================
# SCRAPE DATE (YESTERDAY, US-SAFE)
# =====================================================
# Use local date on runner, not UTC
SCRAPE_DATE = datetime.now() - timedelta(days=1)
# =====================================================
# API CONFIG
# =====================================================
SPORT     = "basketball-women"
DIVISION  = "d1"
CONF_SLUG = "all-conf"
BASE_URL  = "https://ncaa-api.henrygd.me"
REQUEST_TIMEOUT = 20
SLEEP_SECONDS   = 0.30
GAME_ID_RE = re.compile(r"/game/(\d+)")
# =====================================================
# HELPERS
# =====================================================
def get_json(url: str) -> dict:
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()
def scoreboard_url(d: datetime) -> str:
    return (
        f"{BASE_URL}/scoreboard/"
        f"{SPORT}/{DIVISION}/{d:%Y}/{d:%m}/{d:%d}/{CONF_SLUG}"
    )
def boxscore_url(game_id: str) -> str:
    return f"{BASE_URL}/game/{game_id}/boxscore"
def extract_game_ids(scoreboard_json: dict) -> list[str]:
    ids = []
    for item in scoreboard_json.get("games", []):
        game = item.get("game", {}) if isinstance(item, dict) else {}
        url = game.get("url") or item.get("url") or ""
        m = GAME_ID_RE.search(url)
        if m:
            ids.append(m.group(1))
    return sorted(set(ids))
# =====================================================
# SCRAPE SINGLE DATE
# =====================================================
def scrape_date(d: datetime):
    date_tag = d.strftime("%m%d%Y")
    out_path = os.path.join(OUT_DIR, f"{date_tag}_raw.jsonl")
    if os.path.exists(out_path):
        print(f"[SKIP] {d:%Y-%m-%d} already exists")
        return
    sb_url = scoreboard_url(d)
    print(f"\n=== {d:%Y-%m-%d} ===")
    print(f"Scoreboard: {sb_url}")
    try:
        sb = get_json(sb_url)
    except requests.RequestException as e:
        print(f"Scoreboard fetch failed: {e}")
        return
    game_ids = extract_game_ids(sb)
    n_games = len(game_ids)
    print(f"Found {n_games} games")
    if n_games == 0:
        print("No games — skipping file creation.")
        return
    with open(out_path, "w", encoding="utf-8") as f:
        for i, gid in enumerate(game_ids, 1):
            try:
                box = get_json(boxscore_url(gid))
            except requests.RequestException as e:
                print(f"[{i}/{n_games}] ERROR {gid}: {e}")
                continue
            f.write(json.dumps(
                {"game_id": gid, "boxscore": box},
                ensure_ascii=False
            ) + "\n")
            if i % 10 == 0 or i == n_games:
                print(f"Progress: {i}/{n_games}")
            time.sleep(SLEEP_SECONDS)
    print(f"Saved → {out_path}")
# =====================================================
# MAIN
# =====================================================
def main():
    print(f"Running GitHub scrape for {SCRAPE_DATE:%Y-%m-%d}")
    scrape_date(SCRAPE_DATE)
    print("Done.")
if __name__ == "__main__":
    main()
