# WNBA Bayesian Prediction Model

An autonomous, self-improving model that predicts the winner, win probability,
and point spread of every WNBA game. It learns online: after each slate of
games finishes, the results are assimilated into the posterior, so the model
literally improves over the course of a season.

## The model

A **Bayesian conjugate linear regression** on the point spread
(`HomeScore − AwayScore`) with a Normal–Inverse–Gamma prior/posterior
(`model.py`). For a new game the posterior predictive is a Student-t, which
gives both a predicted margin and a calibrated win probability
`P(home wins) = P(spread > 0)`.

The posterior is updated **sequentially** — the current posterior becomes the
prior for the next batch of games — and a season forgetting factor
(`SEASON_DISCOUNT = 0.80`) re-inflates uncertainty each May so the model adapts
to roster turnover and expansion teams without discarding what it learned.

### Features (all leakage-safe, `features.py`)

Every feature is a `home − away` difference computed **only** from games that
finished strictly before the game being predicted, with early-season values
shrunk toward the team's previous-season form (and toward league average for
expansion teams):

| feature | meaning |
|---|---|
| `intercept` | league-average home-court edge |
| `net_diff` | season-to-date average point margin |
| `off_diff` | season-to-date points scored |
| `def_diff` | season-to-date points allowed (defence) |
| `winpct_diff` | season-to-date win percentage |
| `form_diff` | average margin over the last 5 games |
| `rest_diff` | days of rest entering the game (capped) |

All inputs come from the CSVs the existing WNBA data workflow already commits
(`WNBA/game_results_app/data/`), so this pipeline never scrapes anything.

## Backtest

Walk-forward, no look-ahead (burn-in 2024, evaluate 2025 + 2026-to-date):

| metric | value |
|---|---|
| Out-of-sample games | 413 |
| **Winner accuracy** | **64.6%** (home-always baseline 53.8%) |
| Brier score | 0.224 (0.25 = coin flip) |
| Log loss | 0.639 |
| Spread MAE | 10.8 pts |

Results are stable across prior settings, indicating the model is not overfit.
Re-run any time with `python backtest.py` → `accuracy/backtest_summary.json`.

## Layout

```
predictions/
  config.py            paths, seasons, forgetting factor, valid franchises
  features.py          leakage-safe feature engineering
  model.py             Bayesian conjugate spread model
  backtest.py          walk-forward backtest
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
