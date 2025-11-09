#!/usr/bin/env python
"""
Fetch NFL play-by-play (PBP) data from nfl_data_py (nflverse mirror) and save to /NFL/pbp_app/data.

Examples:
  - Full history (1999–current): 
      python NFL/pbp_app/scripts/fetch_pbp.py
  - Specific range (2015–2025) as one combined Parquet:
      python NFL/pbp_app/scripts/fetch_pbp.py --start 2015 --end 2025
  - Year list (comma-separated):
      python NFL/pbp_app/scripts/fetch_pbp.py --years 2019,2020,2024,2025
  - Partition by season (one file per year):
      python NFL/pbp_app/scripts/fetch_pbp.py --start 2019 --end 2025 --partition-by-season
  - Output CSV instead of Parquet:
      python NFL/pbp_app/scripts/fetch_pbp.py --format csv
"""

import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import pandas as pd

try:
    from nfl_data_py import import_pbp_data
except Exception as e:
    print("ERROR: nfl-data-py is not installed. Run: pip install nfl-data-py", file=sys.stderr)
    raise

DEF_FIRST_SEASON = 1999  # nflverse coverage starts 1999
TODAY = dt.date.today()
DEF_LAST_SEASON = TODAY.year  # you can pin to 2025 if you prefer reproducibility

REPO_ROOT_HINT = Path(__file__).resolve().parents[3]  # …/sports_data_library
DEFAULT_OUT_DIR = REPO_ROOT_HINT / "NFL" / "pbp_app" / "data"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download NFL play-by-play from nfl_data_py.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--years", type=str, help="Comma-separated list of seasons, e.g., 2019,2020,2024")
    p.add_argument("--start", type=int, default=DEF_FIRST_SEASON, help=f"Start season (default {DEF_FIRST_SEASON})")
    p.add_argument("--end", type=int, default=DEF_LAST_SEASON, help=f"End season inclusive (default current year)")
    p.add_argument(
        "--out-dir",
        type=str,
        default=str(DEFAULT_OUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUT_DIR})"
    )
    p.add_argument("--format", choices=["parquet", "csv"], default="parquet", help="Output format (default parquet)")
    p.add_argument("--downcast", action="store_true", help="Try to downcast dtypes to reduce file size")
    p.add_argument("--partition-by-season", action="store_true", help="Write one file per season instead of a single file")
    p.add_argument(
        "--outfile",
        type=str,
        default=None,
        help="Custom output filename for combined export (ignored if --partition-by-season)."
    )
    return p.parse_args()


def resolve_years(args: argparse.Namespace) -> list[int]:
    if args.years:
        years = sorted({int(y.strip()) for y in args.years.split(",") if y.strip()})
    else:
        years = list(range(int(args.start), int(args.end) + 1))
    # sanity checks
    years = [y for y in years if y >= DEF_FIRST_SEASON]
    if not years:
        raise ValueError("No valid years to fetch. Check --years / --start / --end.")
    return years


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fetch_pbp(years: list[int], downcast: bool) -> pd.DataFrame:
    # import_pbp_data can take a list of years and handle batching
    print(f"Fetching PBP for {years[0]}–{years[-1]} ({len(years)} seasons)…", flush=True)
    df = import_pbp_data(years, downcast=downcast)
    # nfl_data_py already returns tidy columns; you could optional-select columns here if you want slimmer files.
    # Example to slim (uncomment and customize):
    # keep_cols = ["season","week","game_id","play_id","home_team","away_team","posteam","defteam",
    #              "yardline_100","ydstogo","ydsnet","play_type","pass_length_air_yards","epa","cpoe","score_differential",
    #              "wp","wpa","qtr","game_seconds_remaining","shotgun","no_huddle","rush","pass","complete_pass","interception"]
    # df = df[[c for c in keep_cols if c in df.columns]]
    return df


def write_partitioned(df: pd.DataFrame, out_dir: Path, fmt: str) -> None:
    if "season" not in df.columns:
        raise ValueError("Expected 'season' column to partition by season.")
    seasons = sorted(df["season"].dropna().unique().tolist())
    print(f"Writing {len(seasons)} season files to {out_dir} …")
    for y in seasons:
        part = df[df["season"] == y]
        if fmt == "parquet":
            out_path = out_dir / f"pbp_{y}.parquet"
            part.to_parquet(out_path, index=False)
        else:
            out_path = out_dir / f"pbp_{y}.csv"
            part.to_csv(out_path, index=False)
        print(f"  ✓ {out_path}  ({len(part):,} rows)")


def write_combined(df: pd.DataFrame, out_dir: Path, fmt: str, outfile: str | None, years: list[int]) -> None:
    if outfile:
        out_path = Path(outfile)
        if not out_path.is_absolute():
            out_path = out_dir / outfile
    else:
        yr_min, yr_max = min(years), max(years)
        ext = "parquet" if fmt == "parquet" else "csv"
        out_path = out_dir / f"pbp_{yr_min}_{yr_max}.{ext}"

    if fmt == "parquet":
        df.to_parquet(out_path, index=False)
    else:
        df.to_csv(out_path, index=False)
    print(f"✓ Wrote combined file: {out_path}  ({len(df):,} rows)")


def main():
    args = parse_args()
    years = resolve_years(args)

    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    try:
        df = fetch_pbp(years, downcast=args.downcast)
        # Basic de-dup (just in case):
        if {"game_id", "play_id"}.issubset(df.columns):
            before = len(df)
            df = df.drop_duplicates(subset=["game_id", "play_id"])
            if len(df) != before:
                print(f"De-duplicated plays: {before:,} → {len(df):,}")

        if args.partition_by_season:
            write_partitioned(df, out_dir, args.format)
        else:
            write_combined(df, out_dir, args.format, args.outfile, years)

        print("Done.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
