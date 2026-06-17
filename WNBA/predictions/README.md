# WNBA Bayesian Prediction Model

An autonomous, self-improving model that predicts the winner, win probability,
and point spread of every WNBA game. It learns online: after each slate finishes,
the results are assimilated into the posterior, so the model improves through the
season.

## The model

A **Bayesian conjugate linear regression** on the point spread
(`HomeScore − AwayScore`) with a Normal–Inverse–Gamma prior/posterior
(`model.py`). For a new game the posterior predictive is a Student-t, giving both
a predicted margin and a calibrated win probability `P(home win) = P(spread > 0)`.
The posterior updates **sequentially** — the current posterior becomes the prior
for the next batch — and a season forgetting factor (`SEASON_DISCOUNT = 0.80`)
re-inflates uncertainty each May for roster turnover and expansion teams.

### Features (leakage-safe, `features.py`)

The model is built around an **online Elo rating** as the primary signal:

| feature | meaning |
|---|---|
| `intercept` | league-average home-court edge |
| `elo_diff` | `(home Elo − away Elo) / 100`, pre-game (margin-of-victory weighted, regressed 80% between seasons) |
| `rest_diff` | days of rest entering the game (home − away), capped |

The feature set is deliberately tiny because **walk-forward testing proved that
richer features hurt.** I built and tested opponent-adjusted (strength-of-
schedule) power ratings and pace-adjusted box-score efficiency (`adj_ratings.py`,
retained as a diagnostic), and a raw season-to-date feature set. On out-of-sample
data:

| feature set | winner accuracy |
|---|---|
| raw season-to-date (net/off/def/winpct/form/rest) | 64.7% |
| + opponent-adjusted ratings + box-score efficiency | 64.7% (no gain) |
| **Elo + rest (production)** | **68.7%** |

Elo already captures team strength more cleanly than the noisier proxies, which
only dilute it. Everything comes from the CSVs the WNBA data workflow already
commits (`game_results_app/data/`), so this pipeline never scrapes anything.

## Backtest

Walk-forward, no look-ahead (burn-in 2024, evaluate 2025 + 2026-to-date):

| metric | value |
|---|---|
| Out-of-sample games | 422 |
| **Winner accuracy** | **68.7%** (home-always baseline 54.0%) |
| Brier score | 0.219 (0.25 = coin flip) |
| Log loss | 0.628 |
| Spread MAE | 10.8 pts |

By season: 2025 → 69.8%, 2026 (partial) → 65.8%. For context, the betting
markets — the sharpest predictors that exist — hit roughly 68–70% on WNBA
winners straight up, so this is at the practical ceiling for score-based features.
Re-run any time with `python backtest.py`.

## Layout

```
predictions/
  config.py            paths, seasons, forgetting factor, valid franchises
  features.py          Elo engine + leakage-safe feature vector
  model.py             Bayesian conjugate spread model
  adj_ratings.py       opponent-adjusted / box-score-efficiency ratings (diagnostic)
  backtest.py          walk-forward backtest
  experiment.py        feature-set comparison harness (research)
  predict_day.py       write one day's predictions
  update_results.py    grade finals, learn, refresh accuracy
  run_pipeline.py      orchestrator (backfill | predict | update)
  predictions/<season>/MM_DD_YYYY.csv   daily predictions, per season
  accuracy/
    predictions_history.csv   every graded game (pred vs actual)
    season_accuracy.csv       running accuracy per season
    running_accuracy.csv      cumulative accuracy snapshot per run
    backtest_summary.json     backtest metrics + calibration
  model_state/
    model_current.json        live posterior used for prediction
    model_after_<season>.json  posterior snapshot after each season
```

## Usage

```bash
pip install -r requirements.txt

python run_pipeline.py --mode backfill   # one-off: rebuild full history
python run_pipeline.py --mode predict    # write the next slate
python run_pipeline.py --mode update     # grade finals + learn
python backtest.py                       # re-run the walk-forward backtest
```

## Automation

`.github/workflows/WNBA_predictions.yml` runs daily at 13:00 UTC (May–Oct), an
hour after the data workflow. Each run grades yesterday's finals, updates the
posterior, predicts today's slate, and commits the new files. A manual
`workflow_dispatch` exposes `predict | update | backfill`.

### Yearly maintenance
Before each new season, add the new year to `EVAL_SEASONS` in `config.py` so the
model assimilates the just-finished season.
