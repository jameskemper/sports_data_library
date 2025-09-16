#!/usr/bin/env python3
"""
compile_team_stats.py

- Reads weekly advanced stats CSVs for YEAR
- Flattens 'offense'/'defense' if still nested
- Leaves already flat 'off_*' / 'def_*' columns alone
- Aligns schema to last year's file so 2025 looks like 2024
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

REF_YEAR = str(int(YEAR) - 1)
REF_PATH = os.path.join(BASE_DIR, "data", f"weekly_advanced_stats_{REF_YEAR}.csv")

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
        t = x.strip()
        try:
            return json.loads(t)
        except Exception:
            pass
        try:
            return ast.literal_eval(t)
        except Exception:
            return {}
    return {}

def flatten_one_level(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in (d or {}).items():
        key = to_snake(f"{prefix}{k}")
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out[to_snake(f"{key}_{k2}")] = v2
        else:
            out[key] = v
    return out

def flatten_col(df: pd.DataFrame, col: str, prefix: str) -> pd.DataFrame:
    if col not in df.columns:
        return df
    expanded = df[col].apply(parse_jsonish).apply(flatten_one_level)
    if expanded.apply(bool).any():
        expanded = pd.json_normalize(expanded).add_prefix(prefix)
        df = pd.concat([df.drop(columns=[col]), expanded], axis=1)
    else:
        df = df.drop(columns=[col])
    return df

def load_ref_cols():
    if os.path.exists(REF_PATH):
        return list(pd.read_csv(REF_PATH, nrows=0).columns)
    return []

def order_like_reference(df: pd.DataFrame, ref_cols: list) -> pd.DataFrame:
    if not ref_cols:
        # Put week first if present
        cols = list(df.columns)
        if "week" in cols:
            cols = ["week"] + [c for c in cols if c != "week"]
            df = df[cols]
        return df
    inter = [c for c in ref_cols if c in df.columns]
    extras = [c for c in df.columns if c not in inter]
    return df[inter + extras]

def compile_weekly_stats():
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "advanced_stats_week_*.csv")))
    if not all_files:
        print(f"[warn] No weekly files found for {YEAR}.")
        return

    ref_cols = load_ref_cols()
    df_list = []

    for f in all_files:
        fname = os.path.basename(f)
        week = int(fname.split("_")[-1].replace(".csv", ""))

        df = pd.read_csv(f, low_memory=False)

        if df.empty:
            continue

        # Only flatten if off_/def_ aren’t already present
        has_off_flat = any(c.startswith("off_") for c in df.columns)
        has_def_flat = any(c.startswith("def_") for c in df.columns)
        if not has_off_flat:
            df = flatten_col(df, "offense", "off_")
        if not has_def_flat:
            df = flatten_col(df, "defense", "def_")

        if "week" in df.columns:
            df.drop(columns=["week"], inplace=True)
        df.insert(0, "week", week)

        df = order_like_reference(df, ref_cols)
        df_list.append(df)

    if not df_list:
        print(f"[warn] All weekly files empty for {YEAR}. No output written.")
        return

    combined = pd.concat(df_list, ignore_index=True)
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"[ok] Compiled {len(df_list)} weeks ({combined.shape[0]} rows) → {OUTPUT_FILE}")

if __name__ == "__main__":
    compile_weekly_stats()
