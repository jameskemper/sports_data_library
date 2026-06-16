"""
Feature engineering for the WNBA Bayesian spread model.

Source data
-----------
Everything is derived from the committed game-result CSVs:
    WNBA/game_results_app/data/game_results_<season>.csv
        columns: Date, HomeTeam, HomeScore, AwayTeam, AwayScore, Status, Season
    WNBA/game_results_app/data/schedule_<season>.csv
        columns: Date, Season, HomeTeam, AwayTeam   (future / unplayed games)

Leakage policy (STRICT — this is a *predictive* model)
------------------------------------------------------
For a game played on date D in season S we may only use information from games
that FINISHED STRICTLY BEFORE D. Each team's pre-game rating is its
season-to-date form entering day D, shrunk toward the team's previous-season
final rating (and toward the league average for brand-new / expansion teams).
Nothing about the game being predicted — or anything later — touches its row.

All numeric features are differences (home_value - away_value) so a positive
value favours the HOME team. The intercept therefore absorbs the league-average
home-court advantage. Target = point spread (HomeScore - AwayScore).
"""

import os
import numpy as np
import pandas as pd
from functools import lru_cache

import config as C

# ---------------------------------------------------------------------------
# Feature names (ORDER MATTERS — model coefficients align to this list)
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "intercept",     # league-average home-court edge
    "net_diff",      # season-to-date average point margin (home - away)
    "off_diff",      # season-to-date points scored per game (home - away)
    "def_diff",      # season-to-date points allowed (away_allowed - home_allowed)
    "winpct_diff",   # season-to-date win percentage (home - away)
    "form_diff",     # average margin over last LAST_N games (home - away)
    "rest_diff",     # days of rest entering the game (home - away), capped
]
N_FEATURES = len(FEATURE_COLS)

LAST_N = 5          # recent-form window
PRIOR_WEIGHT = 3.0  # prior-season info worth this many current-season games
REST_CAP = 5        # clamp rest-day advantage to +/- this many days


# ---------------------------------------------------------------------------
# Raw loaders (cached per season)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=32)
def _load_results(season: int) -> pd.DataFrame:
    path = os.path.join(C.GAME_RESULTS_DIR, f"game_results_{season}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    # keep only completed games between two valid franchises
    df = df[df["Status"].astype(str).str.lower().eq("final")]
    df = df[df["HomeTeam"].isin(C.VALID_TEAMS) & df["AwayTeam"].isin(C.VALID_TEAMS)]
    df = df.dropna(subset=["HomeScore", "AwayScore"])
    df["HomeScore"] = df["HomeScore"].astype(float)
    df["AwayScore"] = df["AwayScore"].astype(float)
    return df.sort_values("Date").reset_index(drop=True)


@lru_cache(maxsize=32)
def _load_schedule(season: int) -> pd.DataFrame:
    path = os.path.join(C.GAME_RESULTS_DIR, f"schedule_{season}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[df["HomeTeam"].isin(C.VALID_TEAMS) & df["AwayTeam"].isin(C.VALID_TEAMS)]
    return df.sort_values("Date").reset_index(drop=True)


def clear_caches():
    for fn in (_load_results, _load_schedule, _team_games, _prev_season_rating,
               _league_means):
        try:
            fn.cache_clear()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Per-team long form: one row per (team, game) with that team's PF / PA / win
# ---------------------------------------------------------------------------
@lru_cache(maxsize=32)
def _team_games(season: int) -> pd.DataFrame:
    df = _load_results(season)
    if df.empty:
        return pd.DataFrame(columns=["Date", "team", "pf", "pa", "win", "margin"])
    home = pd.DataFrame({
        "Date": df["Date"], "team": df["HomeTeam"],
        "pf": df["HomeScore"], "pa": df["AwayScore"],
    })
    away = pd.DataFrame({
        "Date": df["Date"], "team": df["AwayTeam"],
        "pf": df["AwayScore"], "pa": df["HomeScore"],
    })
    tg = pd.concat([home, away], ignore_index=True)
    tg["margin"] = tg["pf"] - tg["pa"]
    tg["win"] = (tg["margin"] > 0).astype(float)
    return tg.sort_values("Date").reset_index(drop=True)


@lru_cache(maxsize=32)
def _league_means(season: int):
    """League-average (pf, pa, winpct) for a season — fallback prior for teams
    with no prior-season history (expansion teams)."""
    tg = _team_games(season)
    if tg.empty:
        return {"pf": 81.0, "pa": 81.0, "winpct": 0.5}
    return {"pf": float(tg["pf"].mean()),
            "pa": float(tg["pa"].mean()),
            "winpct": 0.5}


@lru_cache(maxsize=32)
def _prev_season_rating(season: int):
    """{team: dict(pf, pa, winpct)} from the FULL previous season — used as the
    shrinkage prior for early-season games of `season`."""
    prev = _team_games(season - 1)
    if prev.empty:
        return {}
    g = prev.groupby("team").agg(pf=("pf", "mean"), pa=("pa", "mean"),
                                 winpct=("win", "mean"))
    return {t: {"pf": float(r.pf), "pa": float(r.pa), "winpct": float(r.winpct)}
            for t, r in g.iterrows()}


# ---------------------------------------------------------------------------
# Leakage-safe pre-game team rating
# ---------------------------------------------------------------------------
def team_rating(season, date, team):
    """Form of `team` ENTERING `date` in `season`, using only earlier games.

    Returns dict: pf, pa, net, winpct, form, last_date (or None).
    Season-to-date stats are shrunk toward the team's previous-season averages
    (PRIOR_WEIGHT pseudo-games); a team with no prior season falls back to the
    league average.
    """
    date = pd.Timestamp(date)
    tg = _team_games(season)
    past = tg[(tg["team"] == team) & (tg["Date"] < date)] if not tg.empty else tg

    prev = _prev_season_rating(season).get(team)
    league = _league_means(season)
    prior = prev if prev is not None else {"pf": league["pf"],
                                           "pa": league["pa"],
                                           "winpct": league["winpct"]}

    n = len(past)
    w = PRIOR_WEIGHT
    if n == 0:
        pf, pa, winpct = prior["pf"], prior["pa"], prior["winpct"]
        form = 0.0
        last_date = None
    else:
        std_pf = past["pf"].mean()
        std_pa = past["pa"].mean()
        std_wp = past["win"].mean()
        pf = (w * prior["pf"] + n * std_pf) / (w + n)
        pa = (w * prior["pa"] + n * std_pa) / (w + n)
        winpct = (w * prior["winpct"] + n * std_wp) / (w + n)
        form = float(past["margin"].tail(LAST_N).mean())
        last_date = past["Date"].max()

    return {"pf": float(pf), "pa": float(pa), "net": float(pf - pa),
            "winpct": float(winpct), "form": form, "last_date": last_date}


def _rest_days(date, last_date):
    if last_date is None:
        return float(REST_CAP)  # treat season opener as well-rested
    d = (pd.Timestamp(date) - pd.Timestamp(last_date)).days
    return float(np.clip(d, 0, 2 * REST_CAP))


# ---------------------------------------------------------------------------
# Feature vector
# ---------------------------------------------------------------------------
def build_feature_vector(season, date, home_team, away_team):
    h = team_rating(season, date, home_team)
    a = team_rating(season, date, away_team)

    rest_h = _rest_days(date, h["last_date"])
    rest_a = _rest_days(date, a["last_date"])
    rest_diff = float(np.clip(rest_h - rest_a, -REST_CAP, REST_CAP))

    return np.array([
        1.0,
        h["net"] - a["net"],
        h["pf"] - a["pf"],
        a["pa"] - h["pa"],          # positive when home defends better
        h["winpct"] - a["winpct"],
        h["form"] - a["form"],
        rest_diff,
    ], dtype=float)


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------
def build_day_matrix(season, date, games):
    """Vectorise an iterable of (home, away) game tuples for one date."""
    rows, metas = [], []
    for home, away in games:
        try:
            x = build_feature_vector(season, date, home, away)
        except Exception:
            continue
        rows.append(x)
        metas.append({"season": int(season),
                      "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                      "home_team": home, "away_team": away})
    if not rows:
        return np.empty((0, N_FEATURES)), pd.DataFrame()
    return np.vstack(rows), pd.DataFrame(metas)


def build_dataset(seasons):
    """All completed valid games across `seasons`, in chronological order, with
    leakage-safe pre-game features and the realised spread as the target."""
    Xs, metas, ys = [], [], []
    for s in seasons:
        df = _load_results(s)
        for _, gm in df.iterrows():
            try:
                x = build_feature_vector(s, gm["Date"], gm["HomeTeam"], gm["AwayTeam"])
            except Exception:
                continue
            spread = float(gm["HomeScore"] - gm["AwayScore"])
            Xs.append(x)
            ys.append(spread)
            metas.append({
                "season": int(s),
                "date": gm["Date"].strftime("%Y-%m-%d"),
                "home_team": gm["HomeTeam"], "away_team": gm["AwayTeam"],
                "home_score": float(gm["HomeScore"]),
                "away_score": float(gm["AwayScore"]),
                "actual_spread": spread,
                "home_win": int(spread > 0),
            })
    if not Xs:
        return np.empty((0, N_FEATURES)), np.array([]), pd.DataFrame()
    return np.vstack(Xs), np.array(ys), pd.DataFrame(metas)
