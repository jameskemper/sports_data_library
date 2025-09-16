#!/usr/bin/env python3
"""
compile_team_stats.py

- Reads weekly advanced stats CSVs for YEAR
- Flattens any 'offense'/'defense' JSON-ish columns to prefixed columns
- Aligns the final 2025 schema to the 2024 reference schema (same cols, same order)
- Writes data/weekly_advanced_stats_<YEAR>.csv
"""

import os
import glob
import json
import ast
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YEAR = os.environ.get("YEAR", "2025")
DATA_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{YEAR}.csv")

# Use last year's compiled file as the reference schema (so 2025 matches 2024)
REF_YEAR = str(int(YEAR) - 1)
REF_SCHEMA_PATH = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{REF_YEAR}.csv")

def to_snake(s: str) -> str:
    s = s.replace(".", "_").replace("-", "_")
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", s)
    return re.sub(r"__+", "_", s).lower()

def parse_jsonish(x):
    if pd.isna(x):
        return {}
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        x = x.strip()
        # Try JSON first
        try:
            return json.loads(x)
        except Exception:
            pass
        # Then Python literal (dict-like strings)
        try:
            return ast.literal_eval(x)
        except Exception:
            return {}
    return {}

def flatten_nested_dict(d: dict) -> dict:
    """Flatten one level of nesting: {'a':1,'b':{'c':2}} -> {'a':1,'b_c':2} (snake_case)."""
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out[to_snake(f"{k}_{k2}")] = v2
        else:
            out[to_snake(k)] = v
    return out

def flatten_unit(df: pd.DataFrame, col: str, prefix: str) -> pd.DataFrame:
    """If df[col] exists and is JSON-ish, expand it into wide columns with given prefix."""
    if col not in df.columns:
        return df
    expanded = df[col].apply(parse_jsonish).apply(flatten_nested_dict)
    if expanded.apply(bool).any():
        expanded = pd.json_normalize(expanded).add_prefix(prefix)
        df = pd.concat([df.drop(columns=[col]), expanded], axis=1)
    else:
        df = df.drop(columns=[col])
    return df

def load_reference_columns() -> list:
    if os.path.exists(REF_SCHEMA_PATH):
        ref_cols = list(pd.read_csv(REF_SCHEMA_PATH, nrows=0).columns)
        # Ensure 'week' exists in reference (older files should have it; if not, inject)
        if "week" not in ref_cols:
            ref_cols = ["week"] + ref_cols
        return ref_cols
    return []

def align_to_schema(df: pd.DataFrame, ref_cols: list, drop_extras: bool = True) -> pd.DataFrame:
    if not ref_cols:
        return df
    # Add any missing columns
    for c in ref_cols:
        if c not in df.columns:
            df[c] = pd.NA
    # Reorder and optionally drop extras
    if drop_extras:
        df = df[ref_cols]
    else:
        # keep extras at the end
        extras = [c for c in df.columns if c not in ref_cols]
        df = df[ref_cols + extras]
    return df

def compile_weekly_stats():
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "advanced_stats_week_*.csv")))
    if not all_files:
        print("No weekly files found to compile.")
        return

    ref_cols = load_reference_columns()
    df_list = []

    for f in all_files:
        # week from filename (advanced_stats_week_03.csv -> 3)
        fname = os.path.basename(f)
        week = int(fname.split("_")[-1].replace(".csv", ""))

        df = pd.read_csv(f)

        # Normalize potential offense/defense JSON-ish columns to wide columns
        df = flatten_unit(df, "offense", "offense_")
        df = flatten_unit(df, "defense", "defense_")

        # Ensure week column as the first col (and present even if ref doesn't have it)
        df.insert(0, "week", week)

        # Align columns to last year's schema so 2025 looks exactly like 2024
        df = align_to_schema(df, ref_cols, drop_extras=True)

        df_list.append(df)

    combined = pd.concat(df_list, ignore_index=True)

    # (Optional) best-effort numeric cast for metrics (skip obvious IDs/text)
    id_like = {"week", "team", "teamid", "team_id", "opponent", "opponent_id",
               "conference", "home_conference", "away_conference", "season", "season_type"}
    numeric_cols = [c for c in combined.columns if c not in id_like]
    for c in numeric_cols:
        combined[c] = pd.to_numeric(combined[c], errors="ignore")

    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"Compiled {len(df_list)} weeks into {OUTPUT_FILE}")

if __name__ == "__main__":
    compile_weekly_stats()
