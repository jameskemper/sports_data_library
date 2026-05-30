import os
import time
import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamelog

# --------------------------
# Configuration
# --------------------------
SEASON_YEAR = 2026
OUTPUT_DIR  = "NBA/player_box_scores"


def year_to_season_str(year: int) -> str:
    """Convert end-year integer to nba_api season string, e.g. 2026 -> '2025-26'."""
    start = year - 1
    end_yy = str(year)[-2:]
    return f"{start}-{end_yy}"


# --------------------------
# Fetch
# --------------------------
def fetch_season(season_year: int, date_from: str = None, date_to: str = None) -> pd.DataFrame:
    """
    Fetch player box scores for a season.
    date_from / date_to: optional 'MM/DD/YYYY' strings to limit the range.
    """
    season_str = year_to_season_str(season_year)
    range_note = f" from {date_from}" if date_from else " (full season)"
    print(f"Fetching NBA player box scores: {season_str}{range_note} ...")

    all_rows = []
    for season_type in ["Regular Season", "Playoffs"]:
        print(f"  Season type: {season_type}")
        try:
            kwargs = dict(
                season=season_str,
                season_type_all_star=season_type,
                player_or_team_abbreviation="P",   # player-level
                timeout=60,
            )
            if date_from:
                kwargs["date_from_nullable"] = date_from
            if date_to:
                kwargs["date_to_nullable"] = date_to

            log = leaguegamelog.LeagueGameLog(**kwargs)
            df = log.get_data_frames()[0]
            df["season_type"] = season_type
            all_rows.append(df)
            print(f"    -> {len(df):,} rows")
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1.0)

    if not all_rows:
        print("No data retrieved.")
        return pd.DataFrame()

    return pd.concat(all_rows, ignore_index=True)


# --------------------------
# Normalize / Reorder
# --------------------------
def normalize_columns(df: pd.DataFrame, season_year: int) -> pd.DataFrame:
    # isHome: "TOR vs. BOS" = home, "TOR @ BOS" = away
    df["isHome"] = df["MATCHUP"].str.contains(r"\bvs\.", regex=True)

    df = df.rename(columns={
        "GAME_ID":           "gameId",
        "GAME_DATE":         "date",
        "PLAYER_ID":         "playerId",
        "PLAYER_NAME":       "player",
        "TEAM_ID":           "teamId",
        "TEAM_ABBREVIATION": "team",
        "TEAM_NAME":         "teamName",
        "MATCHUP":           "matchup",
        "WL":                "result",
        "season_type":       "seasonType",
        "MIN":               "minutes",
        "FGM":  "fgm",  "FGA":  "fga",  "FG_PCT":  "fg_pct",
        "FG3M": "fg3m", "FG3A": "fg3a", "FG3_PCT": "fg3_pct",
        "FTM":  "ftm",  "FTA":  "fta",  "FT_PCT":  "ft_pct",
        "OREB": "oreb", "DREB": "dreb", "REB":     "reb",
        "AST":  "ast",  "STL":  "stl",  "BLK":     "blk",
        "TOV":  "tov",  "PF":   "pf",   "PTS":     "points",
        "PLUS_MINUS": "plus_minus",
    })

    df["season"] = season_year

    front_cols = [
        "gameId", "date", "season", "seasonType",
        "playerId", "player",
        "teamId", "team", "teamName",
        "isHome", "matchup", "result", "minutes",
        "points", "reb", "ast", "stl", "blk", "tov", "plus_minus",
    ]
    existing_front = [c for c in front_cols if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_front]
    return df[existing_front + remaining]


# --------------------------
# Main
# --------------------------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{SEASON_YEAR}.csv")

    # Determine fetch range: pick up from day after last recorded game
    date_from = None
    if os.path.exists(output_path):
        existing = pd.read_csv(output_path, usecols=["date"])
        if not existing.empty:
            last_date = pd.to_datetime(existing["date"]).max()
            next_date = last_date + timedelta(days=1)
            yesterday = datetime.now() - timedelta(days=1)
            if next_date.date() > yesterday.date():
                print(f"Already up to date through {last_date.date()}. Nothing to fetch.")
                return
            date_from = next_date.strftime("%m/%d/%Y")
            print(f"Existing CSV found. Fetching games from {date_from} onward.")
    else:
        print("No existing CSV. Fetching full season.")

    df_raw = fetch_season(SEASON_YEAR, date_from=date_from)
    if df_raw.empty:
        print("No new games found.")
        return

    df_new = normalize_columns(df_raw, SEASON_YEAR)

    # Append to existing CSV (or write fresh)
    if os.path.exists(output_path):
        existing_full = pd.read_csv(output_path)
        combined = pd.concat([existing_full, df_new], ignore_index=True)
        combined.drop_duplicates(subset=["gameId", "playerId"], inplace=True)
        combined.to_csv(output_path, index=False)
        print(f"Appended {len(df_new):,} new rows. Total: {len(combined):,} -> {output_path}")
    else:
        df_new.to_csv(output_path, index=False)
        print(f"Saved {len(df_new):,} rows -> {output_path}")


if __name__ == "__main__":
    main()
