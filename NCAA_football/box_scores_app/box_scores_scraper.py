#!/usr/bin/env python3
"""
box_scores_scraper.py

Fetches CFBD weekly game/box score data for one week and saves JSON.

- Uses /games for schedules + scores (always available).
- Falls back to /games/box endpoints once stats exist.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
import requests


def build_endpoints(year: int, week: int, season_type: str):
    base = "https://api.collegefootballdata.com"
    q = f"year={year}&week={week}&seasonType={season_type}"

    # /games works even if stats aren't live yet
    return [
        f"{base}/games?{q}",
        f"{base}/games/box/advanced?{q}",
        f"{base}/games/box?{q}",
    ]


def fetch(url: str, headers: dict, tries: int = 3, timeout: int = 20):
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return None
            elif r.status_code == 404:
                return None
        except Exception as e:
            if attempt == tries:
                print(f"Failed: {url} ({e})")
                return None
            time.sleep(2 * attempt)
    return None


def save_json(obj, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--season-type", default="regular")
    args = p.parse_args()

    api_key = os.environ.get("CFBD_API_KEY")
    if not api_key:
        print("Missing CFBD_API_KEY", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / "data" / f"weeks_{args.year}"
    out_path = out_dir / f"week_{args.week:02d}.json"

    headers = {"Authorization": f"Bearer {api_key}", "accept": "application/json"}

    print(f"=== Fetching: year={args.year} week={args.week} type={args.season_type} ===")
    data, url = None, None
    for u in build_endpoints(args.year, args.week, args.season_type):
        payload = fetch(u, headers)
        if payload:
            data, url = payload, u
            break

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "_meta": {
            "year": args.year,
            "week": args.week,
            "season_type": args.season_type,
            "fetched_at": fetched_at,
            "source_url": url,
        },
        "data": data if data else [],
    }
    save_json(payload, out_path)
    print(f"Wrote {out_path} ({'records=' + str(len(data)) if data else 'empty'})")


if __name__ == "__main__":
    main()
