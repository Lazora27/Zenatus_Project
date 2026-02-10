# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from datetime import datetime

# CONFIG
DOC_BASE = Path("/opt/Zenatus_Dokumentation")
LOG_DIR = DOC_BASE / "LOG" / "1h"
LISTING_QT_DIR = DOC_BASE / "Listing" / "Quicktest" / "1h"
LISTING_FB_DIR = DOC_BASE / "Listing" / "Full_backtest" / "1h"
FALLBACK_FILE = DOC_BASE / "Listing" / "fallbacks.txt"

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
    print("[BRIDGE] Syncing Logs to Listings...")
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
        print(f"  -> {json_name}: {len(scripts)} items")

def bridge_queue():
    print("[BRIDGE] Bridging Queue (Quicktest Success -> Full Backtest Working)...")
    qt_success_fp = LISTING_QT_DIR / "indicators_succesful_backtested.json"
    fb_working_fp = LISTING_FB_DIR / "indicators_working.json"
    
    if not qt_success_fp.exists():
        print("  -> No Quicktest Success file found.")
        return

    try:
        with open(qt_success_fp, "r", encoding="utf-8") as f:
            qt_data = json.load(f)
            qt_scripts = set(qt_data.get("scripts", []))
    except:
        qt_scripts = set()
        
    # Check if Quicktest Listing is empty or incomplete
    # If Quicktest logs exist but listing is empty, we might need to resync first
    if not qt_scripts:
        print("  -> Quicktest Success Listing empty. Triggering resync...")
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
        print(f"  -> Added {len(new_scripts)} new scripts to Full Backtest Queue. Total: {len(fb_scripts)}")
    else:
        print("  -> No new scripts to add.")

def check_fallbacks():
    print("[BRIDGE] Checking Fallbacks...")
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
        print(f"  -> Found {len(fallbacks)} fallbacks. Saved to {FALLBACK_FILE}")
    else:
        print("  -> No fallbacks found.")

def main():
    sync_logs_to_listings()
    bridge_queue()
    check_fallbacks()

if __name__ == "__main__":
    main()
