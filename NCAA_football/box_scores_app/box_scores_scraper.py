#!/usr/bin/env python3
"""
box_scores_scraper.py

Fetch CFBD weekly box score data for a given year/week and save raw JSON.

Usage examples:
  python box_scores_scraper.py --year 2025 --week 3
  python box_scores_scraper.py --year 2025 --week 3 --season-type regular
  python box_scores_scraper.py --year 2025 --week 3 --classification both --no-exclude-garbage-time

Outputs:
  data/weeks_<YEAR>/week_##.json
  data/weeks_<YEAR>/week_##.raw.txt   (only when parsing fails, for debugging)
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime, timezone

import requests


# ---------------------------
# Helpers
# ---------------------------

def build_endpoints(
    year: int,
    week: int,
    season_type: str,
    classification: str = "fbs",
    exclude_garbage: bool = True,
) -> List[str]:
    """
    Construct a small cascade of CFBD endpoints. We'll take the first 200 OK that parses as JSON.
    """
    base = "https://api.collegefootballdata.com"

    # classification: 'fbs', 'fcs', or 'both' (omit param for both).
    query_parts = [f"year={year}", f"week={week}", f"seasonType={season_type}"]
    if classification.lower() in ("fbs", "fcs"):
        query_parts.append(f"classification={classification.lower()}")
    if exclude_garbage:
        query_parts.append("excludeGarbageTime=true")

    q = "&".join(query_parts)

    return [
        f"{base}/games/box/advanced?{q}",  # preferred advanced team/player box
        f"{base}/games/box?{q}",           # basic box scores
        f"{base}/box/advanced?{q}",        # legacy/alt route
    ]


def fetch_with_retries(url: str, headers: dict, tries: int = 4, timeout: int = 40) -> Optional[requests.Response]:
    backoff = 1.5
    for attempt in range(1, tries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            # Retry on 429 and 5xx
            if resp.status_code == 429 or resp.status_code >= 500:
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


def try_parse_json(resp: requests.Response) -> Tuple[Optional[object], str, str]:
    """
    Attempt to parse JSON; return (obj_or_None, content_type, text_preview)
    """
    ctype = resp.headers.get("Content-Type", "")
    text = resp.text
    text_preview = (text[:1000] if text else "").replace("\n", " ").replace("\r", " ")
    if "application/json" not in ctype.lower():
        return None, ctype, text_preview
    try:
        return resp.json(), ctype, text_preview
    except Exception:
        return None, ctype, text_preview


def save_json(obj, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def safe_len(x) -> str:
    try:
        return str(len(x))
    except Exception:
        return "unknown"


# ---------------------------
# Main
# ---------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape CFBD box scores for a given year/week.")
    parser.add_argument("--year", type=int, required=True, help="Season year, e.g., 2025")
    parser.add_argument("--week", type=int, required=True, help="Week number (1–16)")
    parser.add_argument("--season-type", default="regular", choices=["regular", "postseason"])
    parser.add_argument("--classification", default="fbs", choices=["fbs", "fcs", "both"],
                        help="Game classification filter; 'both' omits the param")
    parser.add_argument("--exclude-garbage-time", action="store_true", default=True,
                        help="Exclude garbage time (default on)")
    parser.add_argument("--no-exclude-garbage-time", dest="exclude_garbage_time", action="store_false",
                        help="Disable garbage time exclusion")
    # NOTE: default behavior is to overwrite existing files (no skip flag used in workflow)
    parser.add_argument("--skip-if-exists", action="store_true",
                        help="If the week JSON already exists, skip downloading.")
    args = parser.parse_args()

    # CFBD key from env
    api_key = os.environ.get("CFBD_API_KEY")
    if not api_key:
        print("ERROR: CFBD_API_KEY env var is not set.", file=sys.stderr)
        sys.exit(2)

    if not (1 <= args.week <= 16):
        print(f"ERROR: week must be 1–16; got {args.week}", file=sys.stderr)
        sys.exit(2)

    # Output path (relative to this script)
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / "data" / f"weeks_{args.year}"
    out_path = out_dir / f"week_{args.week:02d}.json"

    if args.skip_if_exists and out_path.exists():
        print(f"Skip: {out_path} already exists (use without --skip-if-exists to overwrite).")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "sports_data_library/box_scores_scraper (+github-actions; @jameskemper)",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    endpoints = build_endpoints(
        year=args.year,
        week=args.week,
        season_type=args.season_type,
        classification=args.classification,
        exclude_garbage=args.exclude_garbage_time,
    )

    chosen_url = None
    data = None
    last_ctype = None
    last_preview = None
    last_status = None

    print(f"=== Fetching box scores: year={args.year} week={args.week} season_type={args.season_type} classification={args.classification} excludeGarbageTime={args.exclude_garbage_time} ===")
    for url in endpoints:
        print(f"Trying: {url}")
        resp = fetch_with_retries(url, headers=headers, tries=4, timeout=40)
        if resp is None:
            continue
        last_status = resp.status_code
        parsed, ctype, preview = try_parse_json(resp)
        last_ctype, last_preview = ctype, preview

        if resp.status_code == 200 and parsed is not None:
            data = parsed
            chosen_url = url
            break
        elif resp.status_code == 404:
            print(f"Info: 404 (no data yet) ctype={ctype}")
        else:
            print(f"Info: HTTP {resp.status_code} ctype={ctype} preview='{preview[:180]}...'")

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if data is None:
        # Persist informative stub + raw sidecar for debugging
        payload = {
            "_meta": {
                "year": args.year,
                "week": args.week,
                "season_type": args.season_type,
                "fetched_at_utc": fetched_at,
                "source_url": None,
                "http_status": last_status,
                "content_type": last_ctype,
                "preview": (last_preview or "")[:1000],
            },
            "data": []
        }
        save_json(payload, out_path)
        sidecar = out_path.with_suffix(".raw.txt")
        try:
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            with sidecar.open("w", encoding="utf-8") as f:
                f.write(f"status={last_status}\n")
                f.write(f"content-type={last_ctype}\n")
                f.write("urls-tried:\n")
                for u in endpoints:
                    f.write(f"  - {u}\n")
                f.write(f"\npreview:\n{last_preview}\n")
        except Exception as e:
            print(f"Warn: failed to write sidecar {sidecar}: {e}")
        print(f"Wrote: {out_path} (empty) and {sidecar.name} (debug)")
        return

    payload = {
        "_meta": {
            "year": args.year,
            "week": args.week,
            "season_type": args.season_type,
            "fetched_at_utc": fetched_at,
            "source_url": chosen_url,
        },
        "data": data
    }
    save_json(payload, out_path)
    print(f"Wrote: {out_path}  (records={safe_len(data)})")


if __name__ == "__main__":
    main()
