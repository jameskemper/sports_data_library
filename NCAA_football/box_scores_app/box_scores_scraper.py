#!/usr/bin/env python3
"""
box_scores_scraper.py

Fetch CFBD weekly *box score* data for a given year/week and save raw JSON.

Usage:
  python box_scores_scraper.py --year 2025 --week 3
  python box_scores_scraper.py --year 2025 --week 3 --season-type regular
  python box_scores_scraper.py --year 2025 --week 3 --skip-if-exists

Output:
  box_scores_app/data/weeks_<YEAR>/week_##.json
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests


def build_endpoints(year: int, week: int, season_type: str) -> list[str]:
    """
    CFBD has had multiple box endpoints over time. We try a small cascade
    and accept the first 200 OK response.
    """
    base = "https://api.collegefootballdata.com"
    params = f"year={year}&week={week}&seasonType={season_type}"
    return [
        f"{base}/games/box/advanced?{params}",  # Preferred advanced team/player box
        f"{base}/games/box?{params}",           # Basic box scores
        f"{base}/box/advanced?{params}",        # Legacy/alt route seen in some clients
    ]


def fetch_with_retries(url: str, headers: dict, tries: int = 4, timeout: int = 30) -> Optional[requests.Response]:
    backoff = 1.5
    for attempt in range(1, tries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            # 429/5xx: backoff + retry
            if resp.status_code >= 500 or resp.status_code == 429:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            return resp
        except Exception as e:
            if attempt == tries:
                print(f"ERROR: {url} failed after {tries} attempts: {e}", file=sys.stderr)
                return None
            sleep_s = round(backoff ** attempt, 2)
            print(f"Warn: attempt {attempt} failed for {url} → retrying in {sleep_s}s ({e})")
            time.sleep(sleep_s)
    return None


def save_json(obj, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Scrape CFBD box scores for a given year/week.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--season-type", default="regular", choices=["regular", "postseason"])
    parser.add_argument("--skip-if-exists", action="store_true",
                        help="If the week JSON already exists, skip downloading.")
    args = parser.parse_args()

    api_key = os.environ.get("CFBD_API_KEY")
    if not api_key:
        print("ERROR: CFBD_API_KEY env var is not set.", file=sys.stderr)
        sys.exit(2)

    if not (1 <= args.week <= 16):
        print(f"ERROR: week must be 1–16; got {args.week}", file=sys.stderr)
        sys.exit(2)

    # Output path
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / "data" / f"weeks_{args.year}"
    out_path = out_dir / f"week_{args.week:02d}.json"

    if args.skip_if_exists and out_path.exists():
        print(f"Skip: {out_path} already exists (use without --skip-if-exists to overwrite).")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
        "User-Agent": "sports_data_library/box_scores_scraper (+github actions)"
    }

    endpoints = build_endpoints(args.year, args.week, args.season_type)
    chosen_url = None
    data = None

    print(f"=== Fetching box scores: year={args.year} week={args.week} season_type={args.season_type} ===")
    for url in endpoints:
        print(f"Trying: {url}")
        resp = fetch_with_retries(url, headers=headers, tries=4, timeout=40)
        if resp is None:
            continue
        if resp.status_code == 200:
            try:
                data = resp.json()
            except json.JSONDecodeError:
                print(f"Warn: 200 but JSON parse failed for {url}", file=sys.stderr)
                data = None
            if data is not None:
                chosen_url = url
                break
        elif resp.status_code == 404:
            # 404 likely means no data yet for that week/seasonType; keep trying alternatives
            print(f"Info: {url} returned 404 (no data).")
        else:
            print(f"Info: {url} returned HTTP {resp.status_code}")

    if data is None:
        # Even if nothing was returned, persist an empty list with metadata so downstream stays deterministic.
        print("No box score payload found across tried endpoints; writing empty array with meta.")
        payload = {
            "_meta": {
                "year": args.year,
                "week": args.week,
                "season_type": args.season_type,
                "fetched_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source_url": None,
                "note": "No data returned from any tried endpoint."
            },
            "data": []
        }
        save_json(payload, out_path)
        print(f"Wrote: {out_path} (empty)")
        return

    # Normalize to a consistent envelope so the compiler can rely on a stable shape.
    payload = {
        "_meta": {
            "year": args.year,
            "week": args.week,
            "season_type": args.season_type,
            "fetched_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source_url": chosen_url,
        },
        "data": data
    }

    save_json(payload, out_path)
    print(f"Wrote: {out_path}  (records={len(data) if hasattr(data, '__len__') else 'unknown'})")


if __name__ == "__main__":
    main()
