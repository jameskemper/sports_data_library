import os
import sys
import glob
import re
import pandas as pd

def is_nonempty_file(path: str) -> bool:
    try:
        return os.path.getsize(path) > 0
    except OSError:
        return False

def extract_week_from_filename(path: str) -> int | None:
    # accepts week_01.csv, week-1.csv, 2025_week_12.csv, etc.
    m = re.search(r'week[_\- ]?(\d+)', os.path.basename(path), flags=re.IGNORECASE)
    return int(m.group(1)) if m else None

def main():
    year = os.environ.get("YEAR", "2025")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weeks_dir = os.path.join(base_dir, "data", f"weeks_{year}")
    out_csv = os.path.join(base_dir, "data", f"weekly_advanced_stats_{year}.csv")

    if not os.path.isdir(weeks_dir):
        print(f"[compile_team_stats] No weeks directory: {weeks_dir}")
        # Nothing to compile is not an error; exit 0 so the job doesn't fail.
        sys.exit(0)

    csv_paths = sorted(glob.glob(os.path.join(weeks_dir, "*.csv")))
    if not csv_paths:
        print(f"[compile_team_stats] No weekly CSVs found in {weeks_dir}")
        sys.exit(0)

    frames = []
    bad_files = 0

    for path in csv_paths:
        if not is_nonempty_file(path):
            print(f"[compile_team_stats] Skipping empty file: {path}")
            bad_files += 1
            continue
        try:
            # Read defensively; skip bad lines rather than crash
            df = pd.read_csv(path, low_memory=False, on_bad_lines='skip')
            if df.empty or df.shape[1] == 0:
                print(f"[compile_team_stats] Skipping file with no columns/data: {path}")
                bad_files += 1
                continue
            wk = extract_week_from_filename(path)
            if wk is not None and "week" not in df.columns:
                df["week"] = wk
            if "year" not in df.columns:
                df["year"] = int(year)
            frames.append(df)
        except Exception as e:
            print(f"[compile_team_stats] Failed to read {path}: {e}")
            bad_files += 1

    if not frames:
        print("[compile_team_stats] No valid weekly data to compile. Exiting 0.")
        sys.exit(0)

    compiled = pd.concat(frames, axis=0, ignore_index=True, sort=False)

    # De-dup: prefer a key if present, else exact-row dedup
    dedup_keys = [k for k in ["year", "week", "team", "team_id", "teamid", "conference"] if k in compiled.columns]
    if dedup_keys:
        compiled = compiled.drop_duplicates(subset=dedup_keys, keep="last")
    else:
        compiled = compiled.drop_duplicates(keep="last")

    # Sort if we have typical keys
    sort_keys = [k for k in ["year", "week", "conference", "team", "team_id", "teamid"] if k in compiled.columns]
    if sort_keys:
        compiled = compiled.sort_values(sort_keys).reset_index(drop=True)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    compiled.to_csv(out_csv, index=False)
    print(f"[compile_team_stats] Wrote: {out_csv} ({len(compiled):,} rows; skipped {bad_files} bad/empty files)")

if __name__ == "__main__":
    main()
