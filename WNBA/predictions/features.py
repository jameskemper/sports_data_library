"""
Feature engineering for the WNBA Bayesian spread model.

Source data
-----------
Everything is derived from the committed game-result / schedule CSVs:
    WNBA/game_results_app/data/game_results_<season>.csv
        columns: Date, HomeTeam, HomeScore, AwayTeam, AwayScore, Status, Season
    WNBA/game_results_app/data/schedule_<season>.csv
        columns: Date, Season, HomeTeam, AwayTeam   (future / unplayed games)

The single strongest predictor is an online Elo rating differential. Walk-forward
testing showed that piling raw season-to-date, box-score-efficiency, or
opponent-adjusted features on top of Elo only DILUTES accuracy (they are noisier,
correlated proxies for the same team-strength signal). Rest days add ~1 further
point. So the production feature vector is deliberately tiny:

    [ intercept , elo_diff , rest_diff ]   -> ~68% walk-forward winner accuracy

Leakage policy (STRICT)
-----------------------
Every team's Elo rating is the value ENTERING the game (built by replaying only
earlier results); rest days use the team's previous game date. Nothing about the
game being predicted — or anything later — touches its row. The target is the
realised spread (HomeScore - AwayScore); positive favours the home team and the
Bayesian intercept absorbs the league-average home-court edge.
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
    "intercept",     # league-average home-court edge (Bayesian intercept)
    "elo_diff",      # (home Elo - away Elo) / 100, pre-game, leakage-safe
    "rest_diff",     # days of rest entering the game (home - away), capped
]
N_FEATURES = len(FEATURE_COLS)

LAST_N = 5          # recent-form window (kept for diagnostics / team_rating)
PRIOR_WEIGHT = 3.0  # prior-season info worth this many current-season games
REST_CAP = 5        # clamp rest-day advantage to +/- this many days

# --- Elo configuration ----------------------------------------------------
ELO_BASE = 1500.0
ELO_K = 20.0        # base step; scaled by a log margin-of-victory multiplier
ELO_HOME = 55.0     # home edge used when forming the Elo update expectation
ELO_REG = 0.80      # between-season regression toward the mean (carry 80%)


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
               _league_means, _elo_build):
        try:
            fn.cache_clear()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Online Elo ratings (leakage-safe, replayed from committed game results)
# ---------------------------------------------------------------------------
def _all_seasons():
    return sorted(set(C.BURN_IN_SEASONS) | set(C.EVAL_SEASONS))


@lru_cache(maxsize=1)
def _elo_build():
    """Replay every completed game in chronological order to produce:
        pregame : {(season, 'YYYY-MM-DD', home, away): (elo_home, elo_away)}
                  each team's rating ENTERING that game (pre-game, no leakage).
        current : {team: rating}  after the most recent completed game, with the
                  current season's between-season regression already applied.
    """
    elo = {}
    pregame = {}
    for s in _all_seasons():
        df = _load_results(s)
        if df.empty:
            continue
        for t in list(elo):                       # between-season regression
            elo[t] = ELO_BASE + ELO_REG * (elo[t] - ELO_BASE)
        for _, g in df.iterrows():
            h, a = g["HomeTeam"], g["AwayTeam"]
            eh = elo.get(h, ELO_BASE)
            ea = elo.get(a, ELO_BASE)
            key = (int(s), g["Date"].strftime("%Y-%m-%d"), h, a)
            pregame[key] = (eh, ea)
            exp_h = 1.0 / (1.0 + 10 ** (-((eh + ELO_HOME) - ea) / 400.0))
            res = 1.0 if g["HomeScore"] > g["AwayScore"] else 0.0
            mov = abs(float(g["HomeScore"] - g["AwayScore"]))
            k = ELO_K * np.log(max(mov, 1.0) + 1.0)
            delta = k * (res - exp_h)
            elo[h] = eh + delta
            elo[a] = ea - delta
    return pregame, dict(elo)


def elo_pair(season, date, home, away):
    """Pre-game (elo_home, elo_away). Stored pre-game rating for a game already in
    the results; otherwise (upcoming game) the current ratings after all games."""
    pregame, current = _elo_build()
    key = (int(season), pd.Timestamp(date).strftime("%Y-%m-%d"), home, away)
    if key in pregame:
        return pregame[key]
    return current.get(home, ELO_BASE), current.get(away, ELO_BASE)


def current_elo():
    return _elo_build()[1]


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
    tg = _team_games(season)
    if tg.empty:
        return {"pf": 81.0, "pa": 81.0, "winpct": 0.5}
    return {"pf": float(tg["pf"].mean()), "pa": float(tg["pa"].mean()), "winpct": 0.5}


@lru_cache(maxsize=32)
def _prev_season_rating(season: int):
    prev = _team_games(season - 1)
    if prev.empty:
        return {}
    g = prev.groupby("team").agg(pf=("pf", "mean"), pa=("pa", "mean"),
                                 winpct=("win", "mean"))
    return {t: {"pf": float(r.pf), "pa": float(r.pa), "winpct": float(r.winpct)}
            for t, r in g.iterrows()}


# ---------------------------------------------------------------------------
# Leakage-safe pre-game team form (used for rest + diagnostics)
# ---------------------------------------------------------------------------
def team_rating(season, date, team):
    """Form of `team` ENTERING `date` in `season`, using only earlier games."""
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
        pf = (w * prior["pf"] + n * past["pf"].mean()) / (w + n)
        pa = (w * prior["pa"] + n * past["pa"].mean()) / (w + n)
        winpct = (w * prior["winpct"] + n * past["win"].mean()) / (w + n)
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

    elo_h, elo_a = elo_pair(season, date, home_team, away_team)

    return np.array([
        1.0,
        (elo_h - elo_a) / 100.0,
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
    """All completed valid games across `seasons`, chronological, leakage-safe."""
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
                "home_score": float(gm["HomeScore"]), "away_score": float(gm["AwayScore"]),
                "actual_spread": spread,
                "home_win": int(spread > 0),
            })
    if not Xs:
        return np.empty((0, N_FEATURES)), np.array([]), pd.DataFrame()
    return np.vstack(Xs), np.array(ys), pd.DataFrame(metas)
