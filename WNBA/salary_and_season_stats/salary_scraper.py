"""
WNBA Salary Scraper
Source: Basketball Reference (basketball-reference.com/wnba/years/{year}_salaries.html)

Scrapes player salaries for the current season and saves to
WNBA/salary_and_season_stats/{year}.csv

Skips the year if a CSV already exists.

Run from repo root:
    python WNBA/salary_and_season_stats/salary_scraper.py
"""

import io
import os
import time
import requests
import pandas as pd
from datetime import datetime

# --------------------------
# Configuration
# --------------------------
def get_current_season() -> int:
    return datetime.now().year

SEASON     = get_current_season()
OUTPUT_DIR = "WNBA/salary_and_season_stats"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) "
        "Gecko/20100101 Firefox/123.0"
    )
}


# --------------------------
# Fetch
# --------------------------
def fetch_salaries(year: int) -> pd.DataFrame:
    url = f"https://www.basketball-reference.com/wnba/years/{year}_salaries.html"
    print(f"  Fetching: {url}")
    time.sleep(4)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    tables = pd.read_html(io.StringIO(resp.text))
    if not tables:
        raise ValueError("No tables found on page")

    df = tables[0].copy()

    # Keep only Player and Salary columns
    if "Player" not in df.columns or "Salary" not in df.columns:
        raise ValueError(f"Unexpected columns: {df.columns.tolist()}")

    df = df[["Player", "Salary"]].copy()
    df.columns = ["Player", f"{year} Salary"]

    # Drop repeated header rows
    df = df[df["Player"] != "Player"]
    df = df[df["Player"].notna()]
    df["Player"] = df["Player"].str.strip()
    df[f"{year} Salary"] = df[f"{year} Salary"].astype(str).str.strip()

    return df


# --------------------------
# Main
# --------------------------
def scrape_season(year: int, output_dir: str) -> bool:
    output_path = os.path.join(output_dir, f"{year}.csv")
    if os.path.exists(output_path):
        print(f"  {year}.csv already exists — skipping.")
        return True

    print(f"\n{'='*50}")
    print(f"Scraping WNBA {year} salaries")
    print(f"{'='*50}")

    try:
        df = fetch_salaries(year)
        os.makedirs(output_dir, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"  Saved {len(df)} players -> {output_path}")
        return True
    except Exception as e:
        print(f"  Could not fetch {year}: {e}")
        return False


def main():
    scrape_season(SEASON, OUTPUT_DIR)


if __name__ == "__main__":
    main()
