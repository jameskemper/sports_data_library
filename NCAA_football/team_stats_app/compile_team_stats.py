#!/usr/bin/env python3
"""
compile_team_stats.py

- Reads weekly advanced stats CSVs for YEAR
- Flattens 'offense' and 'defense' JSON into off_* / def_* columns
- Matches exactly the schema of last year's file (2024 by default)
- Writes data/weekly_advanced_stats_<YEAR>.csv
"""

import os
import glob
import json
import ast
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YEAR = os.environ.get("YEAR", "2025")
DATA_DIR = os.path.join(BASE_DIR, "data", f"weeks_{YEAR}")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{YEAR}.csv")

REF_YEAR = str(int(YEAR) - 1)
REF_PATH = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{REF_YEAR}.csv")


def parse_jsonish(x):
    if pd.isna(x):
        return {}
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            try:
                return ast.literal_eval(x)
            except Exception:
                return {}
    return {}


def flatten_col(df: pd.DataFrame, col: str, prefix: str) -> pd.DataFrame:
    if col not in df.columns:
        return df
    expanded = df[col].apply(parse_jsonish).apply(pd.Series).add_prefix(prefix)
    df = pd.concat([df.drop(columns=[col]), expanded], axis=1)
    return df


def load_ref_schema():
    """Load reference column order and dtypes from previous year."""
    if os.path.exists(REF_PATH):
        ref = pd.read_csv(REF_PATH, nrows=100)  # sample for dtypes
        return list(ref.columns), ref.dtypes.to_dict()
    return [], {}


def enforce_schema(df: pd.DataFrame, ref_cols: list, ref_dtypes: dict) -> pd.DataFrame:
    """Restrict df to ref_cols and coerce types."""
    # Keep only reference columns
    df = df[[c for c in ref_cols if c in df.columns]].copy()

    # Enforce dtypes
    for col, dtype in ref_dtypes.items():
        if col in df.columns:
            if "float" in str(dtype) or "int" in str(dtype):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = df[col].astype(str)
    return df


def compile_weekly_stats():
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "advanced_stats_week_*.csv")))
    if not all_files:
        print(f"[warn] No weekly files found for {YEAR}.")
        return

    ref_cols, ref_dtypes = load_ref_schema()
    if not ref_cols:
        print(f"[error] No reference schema found at {REF_PATH}")
        return

    df_list = []

    for f in all_files:
        fname = os.path.basename(f)
        week = int(fname.split("_")[-1].replace(".csv", ""))

        df = pd.read_csv(f, low_memory=False)
        if df.empty:
            continue

        # Flatten offense/defense if present
        df = flatten_col(df, "offense", "off_")
        df = flatten_col(df, "defense", "def_")

        # Insert correct week column
        if "week" in df.columns:
            df.drop(columns=["week"], inplace=True)
        df.insert(0, "week", week)

        # Enforce schema against reference
        df = enforce_schema(df, ref_cols, ref_dtypes)

        df_list.append(df)

    if not df_list:
        print(f"[warn] All weekly files empty for {YEAR}. No output written.")
        return

    combined = pd.concat(df_list, ignore_index=True)
    combined = enforce_schema(combined, ref_cols, ref_dtypes)

    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"[ok] Compiled {len(df_list)} weeks ({combined.shape[0]} rows) → {OUTPUT_FILE}")


if __name__ == "__main__":
    compile_weekly_stats()
