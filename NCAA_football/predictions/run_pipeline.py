"""
Weekly orchestrator for the NCAAF Bayesian model — the single entry point the
scheduled tasks call.

Two modes:
    --mode predict   (run before the week's games)  -> predict_week.py
    --mode update    (run after the week's games)    -> update_results.py

Each mode optionally refreshes raw data first (best-effort; failures are logged
and the model step still runs on whatever data is present):
    1. box_scores_scraper.py --year S --week W   (needs CFBD_API_KEY) + compile
    2. recompile ELO / advanced stats / rankings from any weekly JSON present
       (these compile-only scripts assume the weekly files were fetched
       elsewhere; if they aren't present the existing CSVs are kept).

Season/week are auto-detected from the calendar and box scores unless given.
Out of season there is nothing to do and the model step no-ops safely, so the
tasks can run year-round.

Usage:
    python run_pipeline.py --mode predict
    python run_pipeline.py --mode update
    python run_pipeline.py --mode predict --season 2026 --week 3 --no-scrape
"""

import os
import sys
import subprocess
from datetime import date

import features as F
import config as C
from predict_week import predict_week, _next_unplayed_week
from update_results import update_results, _latest_completed_week

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def current_season(today=None):
    """CFB season label: Aug–Dec -> that year; Jan -> previous year."""
    today = today or date.today()
    return today.year if today.month >= 8 else today.year - 1


def _run(cmd, env_extra=None, cwd=None):
    env = dict(os.environ)
    if env_extra:
        env.update({k: str(v) for k, v in env_extra.items()})
    print(f"  $ {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, timeout=600)
        tail = (r.stdout or "").strip().splitlines()[-3:]
        for line in tail:
            print(f"    {line}")
        if r.returncode != 0:
            err = (r.stderr or "").strip().splitlines()[-2:]
            for line in err:
                print(f"    ! {line}")
        return r.returncode == 0
    except Exception as e:
        print(f"    ! failed: {e}")
        return False


def refresh_data(season, week):
    print(f"[data] refreshing season {season}, around week {week}")
    if not os.environ.get("CFBD_API_KEY"):
        print("  ! CFBD_API_KEY not set — skipping live fetch, using existing CSVs.")
    else:
        bs = os.path.join(REPO, "box_scores_app")
        # Fetch the target week plus the previous one (catch late finals).
        for w in {max(1, week - 1), week}:
            _run([sys.executable, "box_scores_scraper.py", "--year", str(season),
                  "--week", str(w), "--season-type", "regular"], cwd=bs)
        _run([sys.executable, "compile_box_scores_season.py"], env_extra={"YEAR": season}, cwd=bs)

    # Compile-only refreshers (no-op if no new weekly JSON has been dropped in).
    _run([sys.executable, "compile_elo_season.py"],
         env_extra={"YEAR": season}, cwd=os.path.join(REPO, "elo_ratings_app"))
    _run([sys.executable, "compile_team_stats.py"],
         env_extra={"YEAR": season}, cwd=os.path.join(REPO, "team_stats_app"))
    _run([sys.executable, "compile_polls.py"],
         env_extra={"YEAR": season}, cwd=os.path.join(REPO, "rankings_app"))

    # Drop cached loaders so the model sees freshly written CSVs.
    for fn in (F._load_box_scores, F._load_elo, F._load_stats, F._load_rankings,
               F._elo_lookup, F._stats_cumlookup, F._ap_lookup, F._prev_season_stat_means,
               F._load_box_scores, F._ap_lookup):
        try:
            fn.cache_clear()
        except Exception:
            pass


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["predict", "update"], required=True)
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--no-scrape", action="store_true", help="skip data refresh")
    args = ap.parse_args()

    season = args.season or current_season()
    print(f"=== run_pipeline mode={args.mode} season={season} ===")

    if args.mode == "update":
        week = args.week or _latest_completed_week(season)
        if not args.no_scrape:
            refresh_data(season, week or 1)
            week = args.week or _latest_completed_week(season)
        if week is None:
            print("No completed games yet — nothing to update.")
            return
        update_results(season, week)
    else:  # predict
        week = args.week or _next_unplayed_week(season)
        if not args.no_scrape:
            refresh_data(season, week or 1)
            week = args.week or _next_unplayed_week(season)
        if week is None:
            print("No upcoming games found — nothing to predict.")
            return
        predict_week(season, week)


if __name__ == "__main__":
    main()
