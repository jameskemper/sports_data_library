# NCAAF Bayesian Spread & Win-Probability Model

A predictive model for college football games. For any game it produces a
**point-spread estimate** (home minus away) and a **win probability** for each
team (e.g. *Texas Tech 70% / TCU 30%*). It is strictly predictive: every
prediction uses only information available **before kickoff**, and the model is
**Bayesian**, so it updates and improves as results come in.

## How it works

**Model.** A conjugate Bayesian linear regression (Normal–Inverse-Gamma) maps a
small set of pre-game feature differences to the point spread. Because the prior
is conjugate, the posterior has a closed form — no sampling needed — which makes
it fast and trivial to automate.

**Learning over time.** Each week's posterior becomes the prior for the next
week (sequential / online updating). At each season boundary a discount factor
(`SEASON_DISCOUNT`, default 0.80) widens the uncertainty so the model adapts to
roster and coaching turnover without discarding what it learned. Point estimates
are preserved; only the *confidence* (effective sample size) shrinks.

**Win probability** comes from the full posterior-predictive distribution of the
spread (a Student-t), so it reflects both the point estimate and the model's
uncertainty: `P(home win) = P(spread > 0)`.

**Leakage control (the important part for a predictive model).** For a game in
week *W*:

- ELO is the rating carried *into* week *W* (already reflects results through *W−1*).
- Advanced team stats are averaged over weeks *1 … W−1* only (the raw files are
  per-week, so they are accumulated here). Week 1 falls back to the prior
  season's average.
- AP Top 25 rank is the most recent poll with week ≤ *W*.
- Game context: home field, neutral site, conference game.

All features are `home − away` differences, so positive values favor the home team.

## Features used

`elo_diff`, `off_ppa_diff`, `def_ppa_diff`, `off_success_diff`,
`def_success_diff`, `off_expl_diff`, `ap_rank_diff`, `home_field`,
`conference_game`, plus an intercept. (FBS-vs-FBS games only by default, since
ELO/advanced stats cover the 134 FBS teams.)

## Backtest results (walk-forward, 2015–2025)

Burn-in 2010–2014, then genuine week-by-week pre-game predictions 2015–2025
(7,874 games):

| Metric | Value |
|---|---|
| Straight-up winner accuracy | **79.2%** |
| Spread MAE | **10.2 pts** |
| Spread RMSE | 12.6 pts |
| Brier score | 0.141 |
| Log loss | 0.433 |

Win probabilities are well calibrated (see `accuracy/calibration.csv`):
predicted 75% → 72% actual, 85% → 87%, 95% → 96%. Per-season numbers are in
`accuracy/season_accuracy.csv` and are stable (SU 76–83% every year). 2025 is a
fully out-of-sample season (the model had never seen it): 78.6% SU, 10.2 pt MAE.

**Data caveat:** advanced team stats for 2025 are only populated through week 4
(a gap in the upstream team-stats pipeline). The model degrades gracefully —
ELO carries most of the signal — but those features are stale for 2025 weeks 5+.

## Files

| File | Purpose |
|---|---|
| `features.py` | Leakage-safe feature engineering (fast per-season lookups) |
| `model.py` | Bayesian conjugate regression: `update`, `discount`, `predict`, save/load |
| `config.py` | Paths, season ranges, discount factors |
| `backtest.py` | Walk-forward backtest; writes predictions, accuracy, model snapshots |
| `predict_week.py` | Live: predict an upcoming week from the saved posterior |
| `update_results.py` | Live: ingest completed games, update posterior, refresh accuracy |
| `run_pipeline.py` | Weekly orchestrator (data refresh + predict/update); entry point for automation |
| `../../.github/workflows/NCAAF_predictions.yml` | GitHub Actions workflow (runs after the data workflows) |
| `automation/weekly_predictions.yml` | Generic GitHub Actions template (superseded by the workflow above) |
| `predictions/` | Per-season prediction CSVs |
| `accuracy/` | Season accuracy + calibration |
| `model_state/` | Saved posterior snapshots (`model_current.json` = live model) |

## Usage

```bash
pip install -r requirements.txt

# 1. Build the model + full backtest (creates model_current.json):
python backtest.py

# 2. During the season — predict the upcoming week (before games):
python predict_week.py --season 2026 --week 1
#    (no args -> latest season, next unplayed week)

# 3. After the games finish — update the model and accuracy:
python update_results.py --season 2026 --week 1
```

Each prediction CSV row includes: `home_team`, `away_team`, `pred_spread`
(home − away), `win_prob_home`, `pred_winner`, `pred_win_prob`, and the actual
result once played.

## Going live for 2026

1. `model_state/model_current.json` is already built and trained through the
   **2025** season (run `python backtest.py` to rebuild it). Before each new
   season, bump `EVAL_SEASONS` in `config.py` and rerun `backtest.py` so the
   just-finished season is assimilated.
2. `run_pipeline.py` is the single weekly entry point:
   - `python run_pipeline.py --mode predict` — predict the upcoming week
   - `python run_pipeline.py --mode update` — ingest completed games, update the
     posterior and accuracy
   It auto-detects the season (Aug–Dec = that year, January = previous year) and
   the week, and refreshes data best-effort first (skip with `--no-scrape` when
   data is already current, e.g. on the GitHub runner).
3. The posterior in `model_current.json` carries forward and keeps improving.

## GitHub automation

Automated via `.github/workflows/NCAAF_predictions.yml`, a sibling of the
existing data workflows (`NCAAF_box_scores`, `NCAAF_elo_ratings`,
`NCAAF_rankings`, `NCAAF_team_stats`). Those fetch and commit the raw CSVs
daily in-season; the predictions workflow then runs **after** them and consumes
the committed data (`--no-scrape`):

- **Tuesday 13:00 UTC** — `--mode update`: assimilate the weekend's results.
- **Wednesday 13:00 UTC** — `--mode predict`: publish the upcoming week.

It commits `predictions/`, `accuracy/`, and `model_state/` back to `master`, so
the learned posterior persists in the repo from week to week. No API key is
needed (the data is already committed by the other workflows). For local/manual
use, `run_pipeline.py` can also scrape directly if `CFBD_API_KEY` is set.

(The older `automation/weekly_predictions.yml` is kept only as a generic
template; the live workflow is the one in `.github/workflows/`.)

## Tuning knobs (`config.py`)

- `SEASON_DISCOUNT` (0.80): lower = adapts faster to new seasons, higher = more memory.
- `WEEKLY_DISCOUNT` (1.0): set <1 for mild within-season forgetting (recency weighting).
- `BURN_IN_SEASONS` / `EVAL_SEASONS`: change the train/eval split.
- Prior scales live in `BayesianSpreadModel.__init__` (`prior_coef_sd`, `prior_sigma`).

## Possible next steps

- Add a recent-form / opponent-adjusted feature, or rest days from the schedule.
- Calibrate against Vegas closing lines (the data library has them) to measure
  edge, not just accuracy.
- Swap in a hierarchical PyMC version later — the feature/IO layer is reusable.
