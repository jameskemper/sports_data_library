"""
Feature engineering for the NCAAF Bayesian spread model.

Leakage policy (STRICT — this is a *predictive* model):
  For a game in week W of season YYYY we may only use information that
  exists BEFORE that game is played:
    - ELO rating carried INTO week W  (elo_{season}.csv week == W is the
      pre-game rating; it already reflects results through week W-1).
    - Advanced team stats aggregated over weeks 1 .. W-1 (season-to-date).
      The raw weekly_advanced_stats files are PER-WEEK, not cumulative, so we
      average them ourselves through W-1.
    - AP Top 25 ranking from the most recent poll with week <= W.
    - Static game context (home field, neutral site, conference game).

  Week 1 has no within-season stats, so we fall back to the previous
  season's season-long average for that team (still leakage-free).

All numeric features are differences (home_value - away_value) so positive
values favour the HOME team. Target = point spread (home_points - away_points).

Performance: per-season lookups (ELO, cumulative stats, AP rank) are
precomputed once and cached, so building thousands of game vectors is fast.
"""

import os
import bisect
import numpy as np
import pandas as pd
from functools import lru_cache

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BOX_SCORES = os.path.join(BASE, "box_scores_app", "data")
ELO_DIR = os.path.join(BASE, "elo_ratings_app", "data")
STATS_DIR = os.path.join(BASE, "team_stats_app", "data")
RANKS_DIR = os.path.join(BASE, "rankings_app", "data")

# ---------------------------------------------------------------------------
# Feature names (ORDER MATTERS — model coefficients align to this list)
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "intercept",
    "elo_diff",
    "off_ppa_diff",
    "def_ppa_diff",
    "off_success_diff",
    "def_success_diff",
    "off_expl_diff",
    "ap_rank_diff",
    "home_field",
    "conference_game",
]
N_FEATURES = len(FEATURE_COLS)

_STAT_KEYS = ["off_ppa", "def_ppa", "off_successRate", "def_successRate", "off_explosiveness"]
DEFAULT_ELO = 1500.0


# ---------------------------------------------------------------------------
# Raw loaders (cached per season)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=64)
def _load_elo(season: int) -> pd.DataFrame:
    path = os.path.join(ELO_DIR, f"elo_{season}.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


@lru_cache(maxsize=64)
def _load_stats(season: int) -> pd.DataFrame:
    path = os.path.join(STATS_DIR, f"weekly_advanced_stats_{season}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df.loc[:, ~df.columns.duplicated()]


@lru_cache(maxsize=64)
def _load_rankings(season: int) -> pd.DataFrame:
    path = os.path.join(RANKS_DIR, f"weekly_rankings_{season}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "poll" not in df.columns:
        return pd.DataFrame()
    return df[df["poll"] == "AP Top 25"].copy()


@lru_cache(maxsize=64)
def _load_box_scores(season: int) -> pd.DataFrame:
    path = os.path.join(BOX_SCORES, f"box_scores_{season}.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


# ---------------------------------------------------------------------------
# Precomputed per-season lookups
# ---------------------------------------------------------------------------
@lru_cache(maxsize=64)
def _elo_lookup(season: int):
    """{team: (weeks_sorted, elos_aligned)} for fast pre-game ELO lookup."""
    df = _load_elo(season)
    out, rated = {}, set()
    if df.empty:
        return out, rated
    for team, sub in df.sort_values("week").groupby("team"):
        out[team] = (sub["week"].to_numpy(), sub["elo"].to_numpy(dtype=float))
        rated.add(team)
    return out, rated


@lru_cache(maxsize=64)
def _is_cumulative(season: int) -> bool:
    """Detect the storage format of a season's weekly advanced stats.

    Two formats exist in the library:
      - per-week (2010-2024): each week row holds that week's stats, so a volume
        column like off_plays fluctuates week to week.
      - cumulative season-to-date (2025+, via the endWeek scraper): off_plays is
        non-decreasing across weeks.

    We sniff a volume column (off_plays / off_drives) for monotonic
    non-decrease across most teams.
    """
    df = _load_stats(season)
    if df.empty:
        return False
    vol = next((c for c in ("off_plays", "off_drives") if c in df.columns), None)
    if vol is None:
        return False
    mono = total = 0
    for _, sub in df.sort_values("week").groupby("team"):
        v = sub[vol].to_numpy(dtype=float)
        if len(v) < 3:
            continue
        total += 1
        # allow tiny numeric noise
        if np.all(np.diff(v) >= -1e-6):
            mono += 1
    return total > 0 and (mono / total) >= 0.7


@lru_cache(maxsize=64)
def _stats_cumlookup(season: int):
    """{team: (weeks_sorted, value_matrix, keys)} where value_matrix[i] is the
    season-to-date value of each _STAT_KEY entering the week AFTER weeks[i].
    Query for 'weeks < W' takes the row at the largest week strictly below W.

    For per-week data we accumulate a running mean ourselves; for cumulative
    data each row is already season-to-date and is used directly.
    """
    df = _load_stats(season)
    out = {}
    if df.empty:
        return out
    keys = [k for k in _STAT_KEYS if k in df.columns]
    cumulative = _is_cumulative(season)
    for team, sub in df.sort_values("week").groupby("team"):
        sub = sub.dropna(subset=keys, how="all")
        weeks = sub["week"].to_numpy()
        vals = sub[keys].to_numpy(dtype=float)
        if len(weeks) == 0:
            continue
        if cumulative:
            matrix = vals                      # already season-to-date
        else:
            csum = np.cumsum(np.nan_to_num(vals), axis=0)
            cnt = np.arange(1, len(weeks) + 1).reshape(-1, 1)
            matrix = csum / cnt                # running mean
        out[team] = (weeks, matrix, keys)
    return out


@lru_cache(maxsize=64)
def _prev_season_stat_means(season: int):
    """Season-level summary per team, used as the week-1 prior for season+1.

    Per-week season -> mean across weeks. Cumulative season -> the final
    (max-week) row, which already is the full-season-to-date figure.
    """
    df = _load_stats(season)
    if df.empty:
        return {}
    keys = [k for k in _STAT_KEYS if k in df.columns]
    if _is_cumulative(season):
        out = {}
        for team, sub in df.sort_values("week").groupby("team"):
            row = sub.iloc[-1][keys].to_numpy(dtype=float)
            out[team] = dict(zip(keys, row))
        return out
    g = df.groupby("team")[keys].mean()
    return {t: dict(zip(keys, row.to_numpy())) for t, row in g.iterrows()}


@lru_cache(maxsize=64)
def _ap_lookup(season: int):
    """{team: (weeks_sorted, ranks_aligned)}."""
    df = _load_rankings(season)
    out = {}
    if df.empty:
        return out
    for team, sub in df.sort_values("week").groupby("team"):
        out[team] = (sub["week"].to_numpy(), sub["rank"].to_numpy())
    return out


# ---------------------------------------------------------------------------
# Fast leakage-safe getters
# ---------------------------------------------------------------------------
def _get_elo(season, week, team):
    lut, _ = _elo_lookup(season)
    if team not in lut:
        return DEFAULT_ELO
    weeks, elos = lut[team]
    exact = np.where(weeks == week)[0]
    if len(exact):
        return float(elos[exact[0]])
    i = bisect.bisect_left(weeks.tolist(), week)  # first week >= W
    if i > 0:
        return float(elos[i - 1])   # most recent earlier week
    return float(elos[0])


def _get_stats(season, week, team):
    if week > 1:
        lut = _stats_cumlookup(season)
        if team in lut:
            weeks, cummean, keys = lut[team]
            i = bisect.bisect_left(weeks.tolist(), week)  # first week >= W
            if i > 0:
                return dict(zip(keys, cummean[i - 1]))
    if season > 2010:
        prev = _prev_season_stat_means(season - 1)
        if team in prev:
            return prev[team]
    return {}


def _get_ap_rank(season, week, team):
    lut = _ap_lookup(season)
    if team not in lut:
        return 26
    weeks, ranks = lut[team]
    i = bisect.bisect_right(weeks.tolist(), week)  # last week <= W
    if i == 0:
        return 26
    try:
        return int(ranks[i - 1])
    except Exception:
        return 26


def team_is_rated(season, team):
    _, rated = _elo_lookup(season)
    return team in rated


# ---------------------------------------------------------------------------
# Feature vector
# ---------------------------------------------------------------------------
def build_feature_vector(season, week, home_team, away_team,
                         neutral_site, conference_game) -> np.ndarray:
    elo_diff = _get_elo(season, week, home_team) - _get_elo(season, week, away_team)
    hs = _get_stats(season, week, home_team)
    as_ = _get_stats(season, week, away_team)

    def sdiff(k):
        return float(hs.get(k, 0.0)) - float(as_.get(k, 0.0))

    home_rank = _get_ap_rank(season, week, home_team)
    away_rank = _get_ap_rank(season, week, away_team)

    return np.array([
        1.0,
        elo_diff,
        sdiff("off_ppa"),
        -sdiff("def_ppa"),
        sdiff("off_successRate"),
        -sdiff("def_successRate"),
        sdiff("off_explosiveness"),
        away_rank - home_rank,
        0.0 if neutral_site else 1.0,
        1.0 if conference_game else 0.0,
    ], dtype=float)


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------
def games_for_week(season, week, fbs_only=True):
    df = _load_box_scores(season)
    if df.empty:
        return pd.DataFrame()
    g = df[df["week"] == week].copy()
    if fbs_only:
        _, rated = _elo_lookup(season)
        g = g[g["home_team"].isin(rated) & g["away_team"].isin(rated)]
    return g


def build_week_matrix(season, week, fbs_only=True):
    g = games_for_week(season, week, fbs_only=fbs_only)
    rows, metas = [], []
    for _, gm in g.iterrows():
        try:
            x = build_feature_vector(
                int(gm["season"]), int(gm["week"]),
                str(gm["home_team"]), str(gm["away_team"]),
                bool(gm["neutral_site"]), bool(gm["conference_game"]),
            )
        except Exception:
            continue
        hp, ap = gm.get("home_points", np.nan), gm.get("away_points", np.nan)
        completed = bool(gm.get("completed", False)) and pd.notna(hp) and pd.notna(ap)
        rows.append(x)
        metas.append({
            "game_id": gm.get("id", ""),
            "season": int(gm["season"]), "week": int(gm["week"]),
            "home_team": str(gm["home_team"]), "away_team": str(gm["away_team"]),
            "neutral_site": bool(gm["neutral_site"]),
            "conference_game": bool(gm["conference_game"]),
            "completed": completed,
            "home_points": float(hp) if pd.notna(hp) else np.nan,
            "away_points": float(ap) if pd.notna(ap) else np.nan,
            "actual_spread": (float(hp) - float(ap)) if completed else np.nan,
        })
    if not rows:
        return np.empty((0, N_FEATURES)), pd.DataFrame()
    return np.vstack(rows), pd.DataFrame(metas)


def season_weeks(season):
    df = _load_box_scores(season)
    if df.empty:
        return []
    return sorted(int(w) for w in df["week"].dropna().unique())


def build_dataset(seasons, completed_only=True, fbs_only=True):
    Xs, metas = [], []
    for s in seasons:
        for w in season_weeks(s):
            X, meta = build_week_matrix(s, w, fbs_only=fbs_only)
            if len(meta) == 0:
                continue
            if completed_only:
                mask = meta["completed"].values
                X, meta = X[mask], meta[mask].reset_index(drop=True)
            if len(meta):
                Xs.append(X)
                metas.append(meta)
    if not Xs:
        return np.empty((0, N_FEATURES)), pd.DataFrame()
    return np.vstack(Xs), pd.concat(metas, ignore_index=True)
