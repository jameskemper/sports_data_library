import os
import re
import json
import time
import requests
from datetime import datetime, timedelta

# =====================================================
# CONFIGURATION
# =====================================================
START_DATE = datetime(2025, 11, 1)
END_DATE   = datetime(2025, 12, 14)

SPORT      = "basketball-women"
DIVISION   = "d1"
CONF_SLUG  = "all-conf"
BASE_URL   = "https://ncaa-api.henrygd.me"

OUT_DIR = r"C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAAW_basketball\box_scores\2025"
os.makedirs(OUT_DIR, exist_ok=True)

# Networking discipline (CRITICAL)
REQUEST_TIMEOUT = 20      # seconds — prevents hangs
SLEEP_SECONDS   = 0.30    # conservative for large slates

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
# PER-DATE SCRAPER
# =====================================================
def scrape_date(d: datetime):
    date_tag = d.strftime("%m%d%Y")
    out_path = os.path.join(OUT_DIR, f"{date_tag}_raw.jsonl")

    # Skip already-scraped dates
    if os.path.exists(out_path):
        print(f"[SKIP] {d:%Y-%m-%d} → file already exists")
        return

    sb_url = scoreboard_url(d)
    print(f"\n=== {d:%Y-%m-%d} ===")
    print(f"Scoreboard: {sb_url}")

    try:
        sb = get_json(sb_url)
    except requests.RequestException as e:
        print(f"  Scoreboard fetch failed: {e}")
        return

    game_ids = extract_game_ids(sb)
    n_games = len(game_ids)
    print(f"  Found {n_games} games")

    # Skip empty days entirely
    if n_games == 0:
        print("  No games — skipping file creation.")
        return

    saved = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for i, gid in enumerate(game_ids, 1):
            try:
                box = get_json(boxscore_url(gid))
            except requests.Timeout:
                print(f"  [{i}/{n_games}] TIMEOUT → game {gid} skipped")
                continue
            except requests.RequestException as e:
                print(f"  [{i}/{n_games}] ERROR → game {gid}: {e}")
                continue

            f.write(json.dumps(
                {"game_id": gid, "boxscore": box},
                ensure_ascii=False
            ) + "\n")

            saved += 1

            # Heartbeat for large slates
            if i % 10 == 0 or i == n_games:
                print(f"  Progress: {i}/{n_games}")

            time.sleep(SLEEP_SECONDS)

    print(f"  Saved {saved}/{n_games} boxscores → {out_path}")

# =====================================================
# MAIN LOOP
# =====================================================
def main():
    d = START_DATE
    while d <= END_DATE:
        scrape_date(d)
        time.sleep(SLEEP_SECONDS)
        d += timedelta(days=1)

    print("\nDone.")

if __name__ == "__main__":
    main()
