"""
One-time historical backfill for WNBA salary + season stats.
Fetches seasons not already in the folder (skips 2021-2024 which exist).

Basketball Reference WNBA salary data is available from ~2015 onward.
Earlier seasons (pre-2015) may have incomplete or no salary data.

Run from repo root:
    python WNBA/salary_and_season_stats/fetch_historical_salaries.py

Safe to re-run — skips any year that already has a CSV.
Delete this file after use.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from salary_scraper import scrape_season

OUTPUT_DIR = "WNBA/salary_and_season_stats"

# Years not yet in the folder
# 2021-2024 already exist from herhoopsdata.com
# 2015-2020: backfill from Basketball Reference
# 2025: current completed season
START_YEAR = 2015
END_YEAR   = 2025
SKIP_YEARS = {2021, 2022, 2023, 2024}  # already have these

SLEEP_BETWEEN = 3  # extra pause between seasons

def main():
    years = [y for y in range(START_YEAR, END_YEAR + 1) if y not in SKIP_YEARS]
    print(f"Backfilling {len(years)} seasons: {years}\n")

    for year in years:
        scrape_season(year, OUTPUT_DIR)
        time.sleep(SLEEP_BETWEEN)

    print("\nBackfill complete.")

if __name__ == "__main__":
    main()
