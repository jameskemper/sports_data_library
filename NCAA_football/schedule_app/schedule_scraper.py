name: NCAAF Schedule App

on:
  workflow_dispatch:
  schedule:
    # Run every day at 12:00 UTC (07:00 CDT / 06:00 CST), Aug–Jan
    - cron: "0 12 * 8-12,1 *"

permissions:
  contents: write

env:
  YEAR: '2025'

jobs:
  compile-schedule:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        with:
          persist-credentials: true
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests pandas

      - name: Run schedule scraper/compiler
        env:
          CFBD_API_KEY: ${{ secrets.CFBD_API_KEY }}
        run: |
          cd NCAA_football/schedule_app
          python schedule_scraper.py

      - name: Commit & push updated schedule
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          cd NCAA_football/schedule_app

          if [ -f "schedule_${{ env.YEAR }}.csv" ]; then
            git add schedule_${{ env.YEAR }}.csv
          fi

          git diff --cached --quiet || \
            (git commit -m "Automated update: schedule for ${{ env.YEAR }} [skip ci]" && git push origin HEAD)
