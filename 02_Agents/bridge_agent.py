# -*- coding: utf-8 -*-
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Import Config & Logger
try:
    from config_loader import config
    from logger_setup import logger
except ImportError:
    # Fallback setup if run directly without path context
    sys.path.append(os.path.dirname(__file__))
    from config_loader import config
    from logger_setup import logger

# CONFIG
DOC_BASE = config.paths.get("documentation") or Path("/opt/Zenatus_Dokumentation")
LOG_DIR = config.paths.get("logs") / "1h" if config.paths.get("logs") else DOC_BASE / "LOG" / "1h"
LISTING_QT_DIR = config.paths.get("listings") / "Quicktest" / "1h" if config.paths.get("listings") else DOC_BASE / "Listing" / "Quicktest" / "1h"
LISTING_FB_DIR = config.paths.get("listings") / "Full_backtest" / "1h" if config.paths.get("listings") else DOC_BASE / "Listing" / "Full_backtest" / "1h"
FALLBACK_FILE = config.paths.get("listings") / "fallbacks.txt" if config.paths.get("listings") else DOC_BASE / "Listing" / "fallbacks.txt"

# MAPPING LOG FILE -> LISTING FILE
LOG_MAP = {
    "indicators_errors.log": "indicators_errors.json",
    "indicators_no_results.log": "indicators_no_results.json",
    "indicators_successful_backtested.log": "indicators_succesful_backtested.json",
    "indicators_timeout.log": "indicators_timeout.json",
    "indicators_warnings.log": "indicators_warnings.json",
    "indicators_working.log": "indicators_working.json"
}

def load_jsonl(fp):
    items = []
    if not fp.exists():
        return items
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                items.append(json.loads(line))
            except:
                continue
    return items

def write_json_listing(fp, scripts):
    payload = {"scripts": sorted(list(set(scripts)))}
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

def sync_logs_to_listings():
    logger.info("Syncing Logs to Listings...")
    for log_name, json_name in LOG_MAP.items():
        log_fp = LOG_DIR / log_name
        json_fp = LISTING_QT_DIR / json_name
        
        items = load_jsonl(log_fp)
        scripts = []
        for item in items:
            ind = item.get("indicator")
            if ind:
                scripts.append(ind)
        
        # Write to Quicktest Listing
        write_json_listing(json_fp, scripts)
        logger.info(f"Synced {json_name}: {len(scripts)} items")

def bridge_queue():
    logger.info("Bridging Queue (Quicktest Success -> Full Backtest Working)...")
    qt_success_fp = LISTING_QT_DIR / "indicators_succesful_backtested.json"
    fb_working_fp = LISTING_FB_DIR / "indicators_working.json"
    
    if not qt_success_fp.exists():
        logger.warning("No Quicktest Success file found.")
        return

    try:
        with open(qt_success_fp, "r", encoding="utf-8") as f:
            qt_data = json.load(f)
            qt_scripts = set(qt_data.get("scripts", []))
    except Exception as e:
        logger.error(f"Failed to load Quicktest Success file: {e}")
        qt_scripts = set()
        
    # Check if Quicktest Listing is empty or incomplete
    # If Quicktest logs exist but listing is empty, we might need to resync first
    if not qt_scripts:
        logger.warning("Quicktest Success Listing empty. Triggering resync...")
        sync_logs_to_listings()
        try:
            with open(qt_success_fp, "r", encoding="utf-8") as f:
                qt_data = json.load(f)
                qt_scripts = set(qt_data.get("scripts", []))
        except:
            qt_scripts = set()

    try:
        if fb_working_fp.exists():
            with open(fb_working_fp, "r", encoding="utf-8") as f:
                fb_data = json.load(f)
                fb_scripts = set(fb_data.get("scripts", []))
        else:
            fb_scripts = set()
    except:
        fb_scripts = set()
    
    # Logic: Add ALL successful quicktests to Full Backtest working queue
    new_scripts = qt_scripts - fb_scripts
    if new_scripts:
        fb_scripts.update(new_scripts)
        write_json_listing(fb_working_fp, list(fb_scripts))
        logger.info(f"Added {len(new_scripts)} new scripts to Full Backtest Queue. Total: {len(fb_scripts)}")
    else:
        logger.info("No new scripts to add.")

def check_fallbacks():
    logger.info("Checking Fallbacks...")
    warn_log = LOG_DIR / "indicators_warnings.log"
    items = load_jsonl(warn_log)
    fallbacks = set()
    
    for item in items:
        if item.get("reason") == "WARNING_FALLBACK_PARAMS":
            fallbacks.add(item.get("indicator"))
    
    if fallbacks:
        with open(FALLBACK_FILE, "w", encoding="utf-8") as f:
            for name in sorted(list(fallbacks)):
                f.write(name + "\n")
        logger.info(f"Found {len(fallbacks)} fallbacks. Saved to {FALLBACK_FILE}")
    else:
        logger.info("No fallbacks found.")

def main():
    sync_logs_to_listings()
    bridge_queue()
    check_fallbacks()

if __name__ == "__main__":
    main()
