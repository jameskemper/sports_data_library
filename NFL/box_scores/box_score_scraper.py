"""
NFL Box Score Scraper
Scrapes team-level game stats from ESPN's API, organized by week.
GitHub Actions compatible.
"""

import requests
import pandas as pd
import os
import time
from datetime import datetime


def get_nfl_season_year() -> int:
    """
    Auto-detect the current NFL season year.
    The NFL season starts in September, so:
      - Jan-Feb of year Y   -> season Y-1 (playoffs still running)
      - Mar-Aug of year Y   -> season Y-1 (offseason)
      - Sep-Dec of year Y   -> season Y
    """
    now = datetime.now()
    return now.year if now.month >= 9 else now.year - 1


class NFLBoxScoreScraper:
    def __init__(self, season: int, output_dir: str):
        self.season = season
        self.output_dir = output_dir
        self.base_url = "https://site.api.espn.com"
        os.makedirs(output_dir, exist_ok=True)
        print(f"NFL Box Score Scraper — {season} season")
        print(f"Output directory: {output_dir}\n")

    def get_game_ids_for_week(self, week: int, season_type: int = 2) -> list:
        """
        season_type: 2 = regular season, 3 = playoffs
        """
        url = (
            f"{self.base_url}/apis/site/v2/sports/football/nfl/scoreboard"
            f"?week={week}&seasontype={season_type}&dates={self.season}"
        )
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            time.sleep(1)
            data = resp.json()
            return [event["id"] for event in data.get("events", [])]
        except Exception as e:
            print(f"  Error getting game IDs for week {week}: {e}")
            return []

    def get_game_details(self, game_id: str, week: int) -> dict | None:
        url = (
            f"{self.base_url}/apis/site/v2/sports/football/nfl/summary"
            f"?event={game_id}"
        )
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            time.sleep(1)
            data = resp.json()

            game = {"week": week, "season": self.season, "game_id": game_id}

            # Basic info
            if "header" in data and "competitions" in data["header"]:
                comp = data["header"]["competitions"][0]
                game["date"] = comp.get("date", "")
                game["status"] = comp.get("status", {}).get("type", {}).get("description", "")

                competitors = comp.get("competitors", [])
                if len(competitors) >= 2:
                    home = next((c for c in competitors if c["homeAway"] == "home"), competitors[0])
                    away = next((c for c in competitors if c["homeAway"] == "away"), competitors[1])

                    game.update({
                        "away_team":      away["team"]["displayName"],
                        "away_team_abbr": away["team"]["abbreviation"],
                        "away_score":     int(away.get("score", 0)),
                        "home_team":      home["team"]["displayName"],
                        "home_team_abbr": home["team"]["abbreviation"],
                        "home_score":     int(home.get("score", 0)),
                    })
                    game["point_differential"] = abs(game["away_score"] - game["home_score"])
                    if game["away_score"] > game["home_score"]:
                        game["winner"] = game["away_team"]
                    elif game["home_score"] > game["away_score"]:
                        game["winner"] = game["home_team"]
                    else:
                        game["winner"] = "TIE"

            # Team stats
            if "boxscore" in data and "teams" in data["boxscore"]:
                for team_data in data["boxscore"]["teams"]:
                    team_name = team_data["team"]["displayName"]
                    prefix = "away_" if team_name == game.get("away_team") else "home_"

                    for stat in team_data.get("statistics", []):
                        name = stat.get("name", "")
                        val  = stat.get("displayValue", "")

                        # Split composite stats
                        split_map = {
                            "totalPenaltiesYards":  (f"{prefix}penalties",          f"{prefix}penaltyYards",         "-"),
                            "completionAttempts":   (f"{prefix}completions",         f"{prefix}passAttempts",          "/"),
                            "thirdDownEff":         (f"{prefix}thirdDownConversions", f"{prefix}thirdDownAttempts",    "-"),
                            "fourthDownEff":        (f"{prefix}fourthDownConversions",f"{prefix}fourthDownAttempts",   "-"),
                            "sacksYardsLost":       (f"{prefix}sacks",               f"{prefix}sackYardsLost",         "-"),
                        }
                        if name in split_map:
                            k1, k2, sep = split_map[name]
                            if sep in val:
                                parts = val.split(sep, 1)
                                game[k1], game[k2] = parts[0], parts[1]
                            else:
                                game[k1] = val
                        else:
                            game[f"{prefix}{name}"] = val

            # Venue / attendance
            if "gameInfo" in data:
                gi = data["gameInfo"]
                game["attendance"] = gi.get("attendance", "")
                venue = gi.get("venue", {})
                game["venue"]       = venue.get("fullName", "")
                game["venue_city"]  = venue.get("address", {}).get("city", "")
                game["venue_state"] = venue.get("address", {}).get("state", "")

            return game

        except Exception as e:
            print(f"  Error fetching game {game_id}: {e}")
            return None

    def scrape_week(self, week: int, season_type: int = 2) -> pd.DataFrame:
        label = "playoffs" if season_type == 3 else f"week {week}"
        print(f"Scraping {label}...")
        game_ids = self.get_game_ids_for_week(week, season_type)
        if not game_ids:
            print(f"  No games found for {label}")
            return pd.DataFrame()
        print(f"  Found {len(game_ids)} games")
        rows = [self.get_game_details(gid, week) for gid in game_ids]
        rows = [r for r in rows if r]
        df = pd.DataFrame(rows)
        print(f"  Scraped {len(df)} games\n")
        return df

    def save_week(self, df: pd.DataFrame, week: int):
        if df.empty:
            return
        path = os.path.join(self.output_dir, f"week_{week}.csv")
        df.to_csv(path, index=False)
        print(f"Saved: {path} ({len(df)} games)")

    def scrape_season(self, start_week: int = 1, end_week: int = 18,
                      include_playoffs: bool = True):
        print(f"Scraping {self.season} NFL season (weeks {start_week}-{end_week})\n{'='*50}\n")
        for week in range(start_week, end_week + 1):
            df = self.scrape_week(week, season_type=2)
            if not df.empty:
                self.save_week(df, week)

        if include_playoffs:
            # Playoffs: Wild Card=1, Divisional=2, Conference=3, Super Bowl=5
            # ESPN uses season_type=3 with week numbers 1-5
            print("\nScraping playoffs...\n" + "="*50)
            playoff_weeks = {1: "Wild Card", 2: "Divisional", 3: "Conference", 5: "Super Bowl"}
            for pweek, label in playoff_weeks.items():
                df = self.scrape_week(pweek, season_type=3)
                if not df.empty:
                    # Save as week_19, 20, 21, 22 for consistency
                    save_week = 18 + pweek if pweek < 5 else 22
                    self.save_week(df, save_week)

        print(f"\n{'='*50}\nDone. Data saved to: {self.output_dir}")


if __name__ == "__main__":
    SEASON     = int(os.environ.get("NFL_SEASON",    get_nfl_season_year()))
    OUTPUT_DIR = os.environ.get("OUTPUT_DIR",        f"NFL/box_scores/{SEASON}")
    START_WEEK = int(os.environ.get("START_WEEK",    1))
    END_WEEK   = int(os.environ.get("END_WEEK",      18))
    PLAYOFFS   = os.environ.get("INCLUDE_PLAYOFFS",  "true").lower() == "true"

    scraper = NFLBoxScoreScraper(SEASON, OUTPUT_DIR)
    scraper.scrape_season(START_WEEK, END_WEEK, include_playoffs=PLAYOFFS)
