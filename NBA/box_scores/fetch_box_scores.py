import os
import time
import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamelog

# --------------------------
# Configuration
# --------------------------
# NBA season year: 2026 = 2025-26 season
SEASON_YEAR = 2026
OUTPUT_DIR = "NBA/box_scores"


def year_to_season_str(year: int) -> str:
    """Convert end-year integer to nba_api season string, e.g. 2026 -> '2025-26'."""
    start = year - 1
    end_yy = str(year)[-2:]
    return f"{start}-{end_yy}"


# --------------------------
# Fetch (with optional date range)
# --------------------------
def fetch_season(season_year: int, date_from: str = None, date_to: str = None) -> pd.DataFrame:
    """
    Fetch team box scores for a season.
    date_from / date_to: optional 'MM/DD/YYYY' strings to limit the range.
    """
    season_str = year_to_season_str(season_year)
    range_note = f" from {date_from}" if date_from else " (full season)"
    print(f"Fetching NBA box scores: {season_str}{range_note} ...")

    all_rows = []
    for season_type in ["Regular Season", "Playoffs"]:
        print(f"  Season type: {season_type}")
        try:
            kwargs = dict(
                season=season_str,
                season_type_all_star=season_type,
                player_or_team_abbreviation="T",
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
# Add Opponent Stats
# --------------------------
def add_opponent_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Self-join on GAME_ID so each row also has opponent stats as opp_ columns.
    LeagueGameLog returns two rows per game (one per team).
    """
    stat_cols = [
        "FGM", "FGA", "FG_PCT",
        "FG3M", "FG3A", "FG3_PCT",
        "FTM", "FTA", "FT_PCT",
        "OREB", "DREB", "REB",
        "AST", "STL", "BLK", "TOV", "PF", "PTS", "PLUS_MINUS"
    ]

    opp_df = df[["GAME_ID", "TEAM_ID"] + stat_cols].copy()
    opp_df = opp_df.rename(columns={
        "TEAM_ID": "OPP_TEAM_ID",
        **{c: f"opp_{c.lower()}" for c in stat_cols}
    })

    merged = df.merge(opp_df, on="GAME_ID", how="left")
    merged = merged[merged["TEAM_ID"] != merged["OPP_TEAM_ID"]]
    return merged


# --------------------------
# Normalize / Reorder
# --------------------------
def normalize_columns(df: pd.DataFrame, season_year: int) -> pd.DataFrame:
    # isHome: "TOR vs. BOS" = home, "TOR @ BOS" = away
    df["isHome"] = df["MATCHUP"].str.contains(r"\bvs\.", regex=True)

    df = df.rename(columns={
        "GAME_ID":           "gameId",
        "GAME_DATE":         "date",
        "TEAM_ID":           "teamId",
        "TEAM_ABBREVIATION": "team",
        "TEAM_NAME":         "teamName",
        "MATCHUP":           "matchup",
        "WL":                "result",
        "season_type":       "seasonType",
        "OPP_TEAM_ID":       "opponentId",
        "MIN":               "minutes",
        "FGM":  "team_fgm",  "FGA":  "team_fga",  "FG_PCT":  "team_fg_pct",
        "FG3M": "team_fg3m", "FG3A": "team_fg3a", "FG3_PCT": "team_fg3_pct",
        "FTM":  "team_ftm",  "FTA":  "team_fta",  "FT_PCT":  "team_ft_pct",
        "OREB": "team_oreb", "DREB": "team_dreb", "REB":     "team_reb",
        "AST":  "team_ast",  "STL":  "team_stl",  "BLK":     "team_blk",
        "TOV":  "team_tov",  "PF":   "team_pf",   "PTS":     "team_points",
        "PLUS_MINUS": "team_plus_minus",
    })

    df["season"] = season_year

    front_cols = [
        "gameId", "date", "season", "seasonType",
        "teamId", "team", "teamName", "isHome", "matchup", "result", "minutes",
        "opponentId",
        "team_points", "opp_pts",
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
            # Don't bother fetching if we're already current through yesterday
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

    df_new = add_opponent_stats(df_raw)
    df_new = normalize_columns(df_new, SEASON_YEAR)

    # Append to existing CSV (or write fresh)
    if os.path.exists(output_path):
        existing_full = pd.read_csv(output_path)
        combined = pd.concat([existing_full, df_new], ignore_index=True)
        combined.drop_duplicates(subset=["gameId", "teamId"], inplace=True)
        combined.to_csv(output_path, index=False)
        print(f"Appended {len(df_new):,} new rows. Total: {len(combined):,} -> {output_path}")
    else:
        df_new.to_csv(output_path, index=False)
        print(f"Saved {len(df_new):,} rows -> {output_path}")


if __name__ == "__main__":
    main()
