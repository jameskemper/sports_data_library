name: Weekly Box Score Scraper (2025)

on:
  schedule:
    # Noon local in America/Chicago:
    # Aug–Oct is CDT (UTC-5) → 17:00 UTC
    # Nov–Jan is CST (UTC-6) → 18:00 UTC
    - cron: '0 17 * 8,9,10 MON'   # Aug–Oct, 12:00 CDT
    - cron: '0 18 * 11,12,1 MON'  # Nov–Jan, 12:00 CST
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: boxscores-2025
  cancel-in-progress: false

jobs:
  scrape_and_compile:
    runs-on: ubuntu-latest
    env:
      CFBD_API_KEY: ${{ secrets.CFBD_API_KEY }}
      YEAR: "2025"

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pandas requests cfbd

      # If your scraper accepts --year and --week flags (preferred), use this:
      - name: Scrape weeks 1–16 (sequential)
        run: |
          set -e
          for w in $(seq 1 16); do
            echo "=== Scraping YEAR=$YEAR WEEK=$w ==="
            python box_scores_app/box_scores_scraper.py --year "$YEAR" --week "$w" || true
            sleep 1
          done

      # If your script *doesn't* accept CLI args, uncomment this block and comment the one above.
      # It exports WEEK as an env var for each call:
      # - name: Scrape weeks 1–16 (env WEEK fallback)
      #   run: |
      #     set -e
      #     for w in $(seq 1 16); do
      #       echo "=== Scraping YEAR=$YEAR WEEK=$w ==="
      #       YEAR="$YEAR" WEEK="$w" python box_scores_app/box_scores_scraper.py || true
      #       sleep 1
      #     done

      - name: Commit weekly JSON (idempotent)
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "github-actions@github.com"
          git add box_scores_app/data/weeks_${YEAR}/ || true
          git commit -m "Box scores: weeks 1–16 sync for ${YEAR}" || echo "No JSON changes to commit"
          git push || true

      - name: Compile season CSV
        run: |
          python box_scores_app/compile_box_scores_season.py --year "$YEAR" || python box_scores_app/compile_box_scores_season.py

      - name: Commit compiled season file
        run: |
          git add box_scores_app/data/boxscores_${YEAR}.csv || true
          git commit -m "Update boxscores_${YEAR}.csv" || echo "No CSV changes to commit"
          git push || true
