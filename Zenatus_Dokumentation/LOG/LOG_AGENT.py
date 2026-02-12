import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
import shutil
from datetime import datetime
import argparse
import os

BASE = Path(os.environ.get("ZENATUS_BASE_PATH", r"D:\2_Trading\Zenatus\Zenatus_Backtester"))
DOC_ROOT = Path(os.environ.get("ZENATUS_DOC_ROOT", r"D:\2_Trading\Zenatus\Zenatus_Dokumentation\Dokumentation\Fixed_Exit"))
LOG_ROOT = Path(os.environ.get("ZENATUS_LOG_ROOT", r"D:\2_Trading\Zenatus\Zenatus_Dokumentation\LOG"))
UNIQUE_BASE = BASE / "01_Strategy" / "Strategy" / "Unique"
FULL_ALL = BASE / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys"
LOG_FILE_MAP = {
    "indicators_errors.log": "Error",
    "indicators_no_results.log": "No_Results",
    "indicators_successful_backtested.log": "Successful_Backtested",
    "indicators_timeout.log": "Timeout",
    "indicators_warnings.log": "Warning",
    "indicators_working.log": "Working"
}

def has_real_results(ind_basename, timeframe):
    doc_dir = DOC_ROOT / timeframe
    csvs = list(doc_dir.glob(f"*_{ind_basename}.csv"))
    if not csvs:
        return False
    df = pd.read_csv(csvs[0])
    if df.empty:
        return False
    if df.isna().any().any():
        return False
    if "Total_Trades" in df.columns and df["Total_Trades"].max() < 3:
        return False
    return True

def move_indicator(ind_basename, category, timeframe):
    src = FULL_ALL / f"{ind_basename}.py"
    dst_dir = UNIQUE_BASE / timeframe / category
    dst_dir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst_dir / src.name)
        return True
    return False

def iter_log_records(log_dir):
    files = [p for p in log_dir.glob("*.log") if p.name in LOG_FILE_MAP]
    for log_file in files:
        category = LOG_FILE_MAP.get(log_file.name)
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{") and line.endswith("}"):
                    try:
                        obj = json.loads(line)
                    except:
                        continue
                    ind_name = obj.get("indicator")
                    if ind_name:
                        yield log_file, ind_name, category
                elif "Ind#" in line:
                    try:
                        part = line.split("Ind#")[1]
                        ind_num_str = part[:3]
                        ind_num = int(ind_num_str)
                    except:
                        continue
                    candidates = [p.stem for p in FULL_ALL.glob(f"{ind_num:03d}_*.py")]
                    if candidates:
                        yield log_file, candidates[0], category

def run(timeframe, apply_moves=False):
    log_dir = LOG_ROOT / timeframe
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []
    for log_file, ind_basename, category in iter_log_records(log_dir):
        real = has_real_results(ind_basename, timeframe)
        final_category = category
        if category == "Successful_Backtested" and not real:
            final_category = "Working"
        if apply_moves:
            move_indicator(ind_basename, final_category, timeframe)
        results.append({
            "timestamp": now,
            "log": str(log_file),
            "indicator": ind_basename,
            "category": final_category,
            "real_results": real
        })
    listing_dir = Path(os.environ.get("ZENATUS_LISTING_DIR", r"D:\2_Trading\Zenatus\Zenatus_Dokumentation\Listing"))
    listing_dir.mkdir(parents=True, exist_ok=True)
    out = listing_dir / "log_agent_last_run.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"processed": results}, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--timeframe", default="1h")
    args = parser.parse_args()
    run(timeframe=args.timeframe, apply_moves=args.apply)
