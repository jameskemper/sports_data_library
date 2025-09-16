#!/usr/bin/env python3
"""
compile_team_stats.py

Robust compiler for weekly advanced team stats:
- Logs matched weekly files
- Flattens 'offense'/'defense' JSON-ish columns when present
- Aligns column order to last year's file by INTERSECTION (no dropping)
- Writes data/weekly_advanced_stats_<YEAR>.csv
"""

import os
import glob
import json
import ast
import re
import pandas as pd

pd.options.mode.copy_on_write = True

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
        # Try JSON first
        try:
            return json.loads(t)
        except Exception:
            pass
        # Then Python dict literal
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
    expanded = df[col].apply(parse_jsonish).apply(lambda d: flatten_one_level(d))
    # Only expand if we actually got something
    if expanded.apply(bool).any():
        expanded = pd.json_normalize(expanded).add_prefix(prefix)
        df = pd.concat([df.drop(columns=[col]), expanded], axis=1)
    else:
        # Keep things simple—just drop the empty blob column
        df = df.drop(columns=[col])
    return df

def load_ref_cols():
    if os.path.exists(REF_PATH):
        return list(pd.read_csv(REF_PATH, nrows=0).columns)
    return []

def order_like_reference(df: pd.DataFrame, ref_cols: list) -> pd.DataFrame:
    if not ref_cols:
        # Put 'week' first if present
        cols = list(df.columns)
        if "week" in cols:
            cols = ["week"] + [c for c in cols if c != "week"]
            df = df[cols]
        return df
    # Keep only the intersection in ref order, then append any extras
    inter = [c for c in ref_cols if c in df.columns]
    extras = [c for c in df.columns if c not in inter]
    cols = inter + extras
    return df[cols]

def compile_weekly_stats():
    pattern = os.path.join(DATA_DIR, "advanced_stats_week_*.csv")
    all_files = sorted(glob.glob(pattern))
    print(f"[info] YEAR={YEAR}")
    print(f"[info] Searching for weekly files: {pattern}")
    print(f"[info] Found {len(all_files)} files:")
    for f in all_files:
        print(f"  - {os.path.basename(f)}")

    if not all_files:
        print("[warn] No weekly files found. Nothing to compile.")
        # Write an empty file with just headers from reference if we have it (optional)
        if os.path.exists(REF_PATH):
            pd.read_csv(REF_PATH, nrows=0).to_csv(OUTPUT_FILE, index=False)
            print(f"[info] Wrote empty header-only file based on {REF_YEAR}: {OUTPUT_FILE}")
        return

    ref_cols = load_ref_cols()
    df_list = []

    for f in all_files:
        # extract week (advanced_stats_week_03.csv -> 3)
        fname = os.path.basename(f)
        try:
            week = int(fname.split("_")[-1].replace(".csv", ""))
        except Exception:
            print(f"[warn] Could not parse week from filename: {fname}. Skipping.")
            continue

        try:
            # engine='python' for safety with odd quoting; low_memory=False to avoid dtype issues
            df = pd.read_csv(f, low_memory=False, engine="python")
        except Exception as e:
            print(f"[warn] Failed to read {fname}: {e}. Skipping.")
            continue

        if df.empty:
            print(f"[warn] {fname} has 0 rows. Skipping.")
            continue

        # Flatten JSON-ish unit columns if present (case-insensitive fallback)
        cols_lower = {c.lower(): c for c in df.columns}
        for raw, pref in (("offense", "offense_"), ("defense", "defense_")):
            actual = cols_lower.get(raw, cols_lower.get(raw.capitalize()))
            if actual:
                df = flatten_col(df, actual, pref)

        # Insert week as first column
        if "week" in df.columns:
            df.drop(columns=["week"], inplace=True)
        df.insert(0, "week", week)

        df_list.append(df)

    if not df_list:
        print("[error] All weekly files were empty or unreadable. No output written.")
        return

    combined = pd.concat(df_list, ignore_index=True)

    # Order columns to resemble last year's file (intersection first), but keep everything
    combined = order_like_reference(combined, ref_cols)

    # Best-effort numeric cast (skip obvious IDs/text)
    non_numeric_like = {"week", "team", "teamid", "team_id", "opponent", "opponent_id",
                        "conference", "home_conference", "away_conference",
                        "season", "season_type", "team_name", "opponent_name"}
    for c in combined.columns:
        if c not in non_numeric_like:
            combined[c] = pd.to_numeric(combined[c], errors="ignore")

    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"[ok] Compiled {len(df_list)} weeks ({combined.shape[0]} rows) → {OUTPUT_FILE}")

if __name__ == "__main__":
    compile_weekly_stats()
