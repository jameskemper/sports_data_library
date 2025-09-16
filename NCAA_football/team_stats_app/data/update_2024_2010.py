#!/usr/bin/env python3
"""
fix_team_stats_vars.py

Renames dot-notation columns in weekly_advanced_stats_<YEAR>.csv
(2010–2024) to match the 2025 schema (off_* / def_*).
"""

import os
import pandas as pd

BASE_DIR = r"C:\Users\jkemper\OneDrive - Texas Tech University\Git\sports_data_library\NCAA_football\team_stats_app\data"

# Mapping from dot-notation to 2025 style
rename_map = {
    # Offense
    "offense.plays": "off_plays",
    "offense.drives": "off_drives",
    "offense.ppa": "off_ppa",
    "offense.totalPPA": "off_totalPPA",
    "offense.successRate": "off_successRate",
    "offense.explosiveness": "off_explosiveness",
    "offense.powerSuccess": "off_powerSuccess",
    "offense.stuffRate": "off_stuffRate",
    "offense.lineYards": "off_lineYards",
    "offense.lineYardsTotal": "off_lineYardsTotal",
    "offense.secondLevelYards": "off_secondLevelYards",
    "offense.secondLevelYardsTotal": "off_secondLevelYardsTotal",
    "offense.openFieldYards": "off_openFieldYards",
    "offense.openFieldYardsTotal": "off_openFieldYardsTotal",
    "offense.totalOpportunies": "off_totalOpportunies",
    "offense.pointsPerOpportunity": "off_pointsPerOpportunity",
    "offense.fieldPosition.averageStart": "off_fieldPosition",
    "offense.fieldPosition.averagePredictedPoints": "off_fieldPosition",
    "offense.havoc.total": "off_havoc",
    "offense.havoc.frontSeven": "off_havoc",
    "offense.havoc.db": "off_havoc",
    "offense.standardDowns.rate": "off_standardDowns",
    "offense.standardDowns.ppa": "off_standardDowns",
    "offense.standardDowns.successRate": "off_standardDowns",
    "offense.standardDowns.explosiveness": "off_standardDowns",
    "offense.passingDowns.rate": "off_passingDowns",
    "offense.passingDowns.ppa": "off_passingDowns",
    "offense.passingDowns.successRate": "off_passingDowns",
    "offense.passingDowns.explosiveness": "off_passingDowns",
    "offense.rushingPlays.rate": "off_rushingPlays",
    "offense.rushingPlays.ppa": "off_rushingPlays",
    "offense.rushingPlays.totalPPA": "off_rushingPlays",
    "offense.rushingPlays.successRate": "off_rushingPlays",
    "offense.rushingPlays.explosiveness": "off_rushingPlays",
    "offense.passingPlays.rate": "off_passingPlays",
    "offense.passingPlays.ppa": "off_passingPlays",
    "offense.passingPlays.totalPPA": "off_passingPlays",
    "offense.passingPlays.successRate": "off_passingPlays",
    "offense.passingPlays.explosiveness": "off_passingPlays",

    # Defense
    "defense.plays": "def_plays",
    "defense.drives": "def_drives",
    "defense.ppa": "def_ppa",
    "defense.totalPPA": "def_totalPPA",
    "defense.successRate": "def_successRate",
    "defense.explosiveness": "def_explosiveness",
    "defense.powerSuccess": "def_powerSuccess",
    "defense.stuffRate": "def_stuffRate",
    "defense.lineYards": "def_lineYards",
    "defense.lineYardsTotal": "def_lineYardsTotal",
    "defense.secondLevelYards": "def_secondLevelYards",
    "defense.secondLevelYardsTotal": "def_secondLevelYardsTotal",
    "defense.openFieldYards": "def_openFieldYards",
    "defense.openFieldYardsTotal": "def_openFieldYardsTotal",
    "defense.totalOpportunies": "def_totalOpportunies",
    "defense.pointsPerOpportunity": "def_pointsPerOpportunity",
    "defense.fieldPosition.averageStart": "def_fieldPosition",
    "defense.fieldPosition.averagePredictedPoints": "def_fieldPosition",
    "defense.havoc.total": "def_havoc",
    "defense.havoc.frontSeven": "def_havoc",
    "defense.havoc.db": "def_havoc",
    "defense.standardDowns.rate": "def_standardDowns",
    "defense.standardDowns.ppa": "def_standardDowns",
    "defense.standardDowns.successRate": "def_standardDowns",
    "defense.standardDowns.explosiveness": "def_standardDowns",
    "defense.passingDowns.rate": "def_passingDowns",
    "defense.passingDowns.ppa": "def_passingDowns",
    "defense.passingDowns.totalPPA": "def_passingDowns",
    "defense.passingDowns.successRate": "def_passingDowns",
    "defense.passingDowns.explosiveness": "def_passingDowns",
    "defense.rushingPlays.rate": "def_rushingPlays",
    "defense.rushingPlays.ppa": "def_rushingPlays",
    "defense.rushingPlays.totalPPA": "def_rushingPlays",
    "defense.rushingPlays.successRate": "def_rushingPlays",
    "defense.rushingPlays.explosiveness": "def_rushingPlays",
    "defense.passingPlays.rate": "def_passingPlays",
    "defense.passingPlays.ppa": "def_passingPlays",
    "defense.passingPlays.totalPPA": "def_passingPlays",
    "defense.passingPlays.successRate": "def_passingPlays",
    "defense.passingPlays.explosiveness": "def_passingPlays",
}

def process_file(year):
    fname = os.path.join(BASE_DIR, f"weekly_advanced_stats_{year}.csv")
    if not os.path.exists(fname):
        print(f"❌ Missing: {fname}")
        return
    df = pd.read_csv(fname)
    df = df.rename(columns=rename_map)
    df.to_csv(fname, index=False)
    print(f"✅ Fixed: {fname}")

def main():
    for year in range(2010, 2025):  # all years up to 2024
        process_file(year)

if __name__ == "__main__":
    main()
