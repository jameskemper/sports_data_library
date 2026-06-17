"""
Opponent-adjusted (strength-of-schedule) team ratings for the WNBA model.

Two ridge-regularised rating systems, both recomputed leakage-safe as of a given
cutoff date (only games that FINISHED STRICTLY BEFORE the cutoff are used):

1. Adjusted NET rating (from final margins, always available)
       margin_g = hca + r_home - r_away + eps
   Solved by ridge least squares for team strengths r (penalised toward the
   team's previous-season rating) and a free home-court term `hca`.

2. Adjusted OFFENSE / DEFENSE efficiency (points per 100 possessions, from box
   scores)
       ORtg_home = mu + off_home - def_away + hca_off
       ORtg_away = mu + off_away - def_home
   Solved jointly for per-team off/def ratings (penalised toward prior season),
   a free league mean `mu`, and a free `hca_off`. A team's adjusted efficiency
   net is off_t - def_t.

Ridge shrinkage means that with few games a team's rating sits near its prior
(previous-season rating, or league average for an expansion team) and tightens
as the season accumulates — a natural, leakage-free early-season prior.

Everything is cached per (season, cutoff-date) so the walk-forward backtest and
the daily pipeline stay fast.
"""

import os
import numpy as np
import pandas as pd
from functools import lru_cache

import config as C
import features as F

# Ridge penalties (in "pseudo-games" of prior weight). Larger => more shrinkage.
LAMBDA_NET = 6.0
LAMBDA_EFF = 8.0
POSS_MIN = 40.0   # guard against malformed box rows


# ---------------------------------------------------------------------------
# Box-score efficiency table  (date, team) -> points, possessions
# ---------------------------------------------------------------------------
@lru_cache(maxsize=16)
def _box(season: int) -> pd.DataFrame:
    path = os.path.join(C.BASE, "box_scores_app", "data", f"boxscores_{season}.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "team", "pts", "poss"])
    df = pd.read_csv(path)
    df = df[df["TeamName"].isin(C.VALID_TEAMS)].copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["pts"] = 2 * df["FGM"] + df["3PM"] + df["FTM"]
    df["poss"] = df["FGA"] - df["offensiveRebounds"] + df["turnovers"] + 0.44 * df["FTA"]
    df = df[df["poss"] >= POSS_MIN]
    return df[["Date", "TeamName", "pts", "poss"]].rename(columns={"TeamName": "team"})


def _games_before(season, cutoff):
    """Completed games (home, away, margin, + box efficiency where available)
    strictly before `cutoff`."""
    res = F._load_results(season)
    if res.empty:
        return pd.DataFrame()
    g = res[res["Date"] < pd.Timestamp(cutoff)].copy()
    if g.empty:
        return g
    bx = _box(season)
    if not bx.empty:
        bh = bx.rename(columns={"team": "HomeTeam", "pts": "h_pts", "poss": "h_poss"})
        ba = bx.rename(columns={"team": "AwayTeam", "pts": "a_pts", "poss": "a_poss"})
        g = g.merge(bh, on=["Date", "HomeTeam"], how="left")
        g = g.merge(ba, on=["Date", "AwayTeam"], how="left")
    else:
        g["h_poss"] = g["a_poss"] = np.nan
    g["margin"] = g["HomeScore"] - g["AwayScore"]
    return g


# ---------------------------------------------------------------------------
# Ridge solvers
# ---------------------------------------------------------------------------
def _solve_net(games, teams, prior):
    """Ridge for margin = hca + r_home - r_away. Returns {team: rating}, hca."""
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    rows, b = [], []
    for _, gm in games.iterrows():
        row = np.zeros(n + 1)
        row[idx[gm["HomeTeam"]]] = 1.0
        row[idx[gm["AwayTeam"]]] = -1.0
        row[n] = 1.0  # hca
        rows.append(row)
        b.append(gm["margin"])
    A = np.array(rows)
    b = np.array(b, dtype=float)
    # penalty: shrink team ratings toward prior; leave hca free
    P = np.eye(n + 1) * LAMBDA_NET
    P[n, n] = 1e-6
    target = np.zeros(n + 1)
    for t, i in idx.items():
        target[i] = prior.get(t, 0.0)
    x = np.linalg.solve(A.T @ A + P, A.T @ b + P @ target)
    return {t: float(x[i]) for t, i in idx.items()}, float(x[n])


def _solve_eff(games, teams, prior_off, prior_def):
    """Ridge for ORtg = mu + off - def (+hca_off on home row).
    Returns {team: off}, {team: def}."""
    g = games.dropna(subset=["h_poss", "a_poss"])
    if len(g) < 5:
        return {}, {}
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    # unknowns: off[0..n-1], def[0..n-1], mu, hca_off
    OFF, DEF, MU, HCA = 0, n, 2 * n, 2 * n + 1
    rows, b = [], []
    for _, gm in g.iterrows():
        h, a = gm["HomeTeam"], gm["AwayTeam"]
        ortg_h = 100.0 * gm["HomeScore"] / gm["h_poss"]
        ortg_a = 100.0 * gm["AwayScore"] / gm["a_poss"]
        r1 = np.zeros(2 * n + 2); r1[OFF + idx[h]] = 1; r1[DEF + idx[a]] = -1; r1[MU] = 1; r1[HCA] = 1
        r2 = np.zeros(2 * n + 2); r2[OFF + idx[a]] = 1; r2[DEF + idx[h]] = -1; r2[MU] = 1
        rows += [r1, r2]; b += [ortg_h, ortg_a]
    A = np.array(rows); b = np.array(b, dtype=float)
    P = np.eye(2 * n + 2) * LAMBDA_EFF
    P[MU, MU] = 1e-6; P[HCA, HCA] = 1e-6
    target = np.zeros(2 * n + 2)
    for t, i in idx.items():
        target[OFF + i] = prior_off.get(t, 0.0)
        target[DEF + i] = prior_def.get(t, 0.0)
    x = np.linalg.solve(A.T @ A + P, A.T @ b + P @ target)
    off = {t: float(x[OFF + i]) for t, i in idx.items()}
    deff = {t: float(x[DEF + i]) for t, i in idx.items()}
    return off, deff


# ---------------------------------------------------------------------------
# Prior-season full ratings (used as shrinkage target)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=16)
def _prior_net(season):
    g = _games_before(season, pd.Timestamp(f"{season}-12-31"))
    if g.empty:
        return {}
    teams = sorted(set(g["HomeTeam"]) | set(g["AwayTeam"]))
    r, _ = _solve_net(g, teams, {})
    return r


@lru_cache(maxsize=16)
def _prior_eff(season):
    g = _games_before(season, pd.Timestamp(f"{season}-12-31"))
    if g.empty:
        return {}, {}
    teams = sorted(set(g["HomeTeam"]) | set(g["AwayTeam"]))
    return _solve_eff(g, teams, {}, {})


# ---------------------------------------------------------------------------
# Public: adjusted ratings as of a cutoff date (leakage-safe)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4096)
def ratings_asof(season: int, cutoff_str: str):
    """Return dict of per-team adjusted ratings entering `cutoff_str`:
       {team: {net, off, deff, eff_net}}.  Teams with no data -> zeros."""
    cutoff = pd.Timestamp(cutoff_str)
    g = _games_before(season, cutoff)
    prior_net = _prior_net(season - 1)
    prior_off, prior_def = _prior_eff(season - 1)

    if g.empty:
        teams = sorted(C.VALID_TEAMS)
        return {t: {"net": prior_net.get(t, 0.0),
                    "off": prior_off.get(t, 0.0),
                    "deff": prior_def.get(t, 0.0),
                    "eff_net": prior_off.get(t, 0.0) - prior_def.get(t, 0.0)}
                for t in teams}

    teams = sorted(set(g["HomeTeam"]) | set(g["AwayTeam"]) | C.VALID_TEAMS)
    net, _hca = _solve_net(g, teams, prior_net)
    off, deff = _solve_eff(g, teams, prior_off, prior_def)
    out = {}
    for t in teams:
        o = off.get(t, prior_off.get(t, 0.0))
        d = deff.get(t, prior_def.get(t, 0.0))
        out[t] = {"net": net.get(t, prior_net.get(t, 0.0)),
                  "off": o, "deff": d, "eff_net": o - d}
    return out


def clear_caches():
    for fn in (_box, _prior_net, _prior_eff, ratings_asof):
        try:
            fn.cache_clear()
        except Exception:
            pass
