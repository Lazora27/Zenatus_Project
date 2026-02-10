# -*- coding: utf-8 -*-
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# CONFIG
DOC_BASE = Path("/opt/Zenatus_Dokumentation")
LISTING_BASE = DOC_BASE / "Listing" / "Full_backtest"
LOG_BASE = DOC_BASE / "LOG"

TIMEFRAMES = ["1h", "30m", "15m", "5m", "1m", "4h", "1d"]

# ORDER OF PROPAGATION (Hierarchy)
# If a strategy succeeds in a "higher" TF, it propagates to "lower" TFs?
# Or just: Source TF -> All other Target TFs (excluding those already done)
# User said: "One Hour Success -> 30m Working, 15m Working..."
# "30m Success -> 15m Working, etc. BUT NOT 1h (already done)"
# This implies we propagate to ALL TFs that are NOT "Source" AND NOT "Done".

def load_json_list(fp):
    if not fp.exists(): return set()
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("scripts", []))
    except:
        return set()

def save_json_list(fp, items):
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump({"scripts": sorted(list(items))}, f, indent=2, ensure_ascii=False)

def read_log_entries(log_fp):
    entries = []
    if not log_fp.exists(): return entries
    try:
        with open(log_fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    entries.append(json.loads(line))
                except: continue
    except: pass
    return entries

def sync_timeframe(tf):
    print(f"=== SYNCING {tf} ===")
    
    log_dir = LOG_BASE / tf
    listing_dir = LISTING_BASE / tf
    
    # 1. Read Logs
    success_log = log_dir / "indicators_successful_backtested.log"
    error_log = log_dir / "indicators_errors.log"
    timeout_log = log_dir / "indicators_timeout.log"
    nores_log = log_dir / "indicators_no_results.log"
    
    success_entries = read_log_entries(success_log)
    error_entries = read_log_entries(error_log)
    timeout_entries = read_log_entries(timeout_log)
    nores_entries = read_log_entries(nores_log)
    
    # 2. Extract Strategy Names
    success_set = {e["indicator"] for e in success_entries}
    error_set = {e["indicator"] for e in error_entries}
    timeout_set = {e["indicator"] for e in timeout_entries}
    nores_set = {e["indicator"] for e in nores_entries}
    
    # 3. Update Listings
    # Load existing to merge? Or rebuild from logs?
    # Usually logs are append-only truth. Listings reflect current state.
    # Ideally, we add new log entries to listings.
    
    # Load current listings
    l_success = load_json_list(listing_dir / "indicators_succesful_backtested.json")
    l_errors = load_json_list(listing_dir / "indicators_errors.json")
    l_timeout = load_json_list(listing_dir / "indicators_timeout.json")
    l_nores = load_json_list(listing_dir / "indicators_no_results.json")
    l_working = load_json_list(listing_dir / "indicators_working.json")
    
    # Update
    l_success.update(success_set)
    l_errors.update(error_set)
    l_timeout.update(timeout_set)
    l_nores.update(nores_set)
    
    # Clean up 'working'
    # If in success/error/timeout/nores, remove from working
    to_remove = l_success | l_errors | l_timeout | l_nores
    l_working = l_working - to_remove
    
    # Save
    save_json_list(listing_dir / "indicators_succesful_backtested.json", l_success)
    save_json_list(listing_dir / "indicators_errors.json", l_errors)
    save_json_list(listing_dir / "indicators_timeout.json", l_timeout)
    save_json_list(listing_dir / "indicators_no_results.json", l_nores)
    save_json_list(listing_dir / "indicators_working.json", l_working)
    
    print(f"  Updated Listings for {tf}:")
    print(f"    Success: {len(l_success)}")
    print(f"    Working: {len(l_working)}")
    
    return l_success

def propagate_strategies(source_tf, success_strategies):
    print(f"=== PROPAGATING FROM {source_tf} ===")
    
    for target_tf in TIMEFRAMES:
        if target_tf == source_tf: continue
        
        target_listing_dir = LISTING_BASE / target_tf
        
        # Check if Target is "Done" or "Source-like"?
        # User said: "Resultate nicht an eine Stunde gesendet werden, weil wir eine Stunde ja dann bereits haben"
        # This implies we check if the strategy is ALREADY in Success of Target.
        
        target_success = load_json_list(target_listing_dir / "indicators_succesful_backtested.json")
        target_working = load_json_list(target_listing_dir / "indicators_working.json")
        
        # Strategies to add
        # Only add if NOT in Target Success AND NOT in Target Working (to avoid dups)
        to_add = []
        for s in success_strategies:
            if s not in target_success and s not in target_working:
                to_add.append(s)
                
        if to_add:
            target_working.update(to_add)
            save_json_list(target_listing_dir / "indicators_working.json", target_working)
            print(f"  -> Propagated {len(to_add)} strategies to {target_tf} Working")
        else:
            print(f"  -> No new strategies for {target_tf}")

def main():
    print(f"[{datetime.now().isoformat()}] STARTING LOG SYNC & PROPAGATION")
    
    # 1. Sync & Get Successes for ALL Timeframes
    tf_successes = {}
    for tf in TIMEFRAMES:
        tf_successes[tf] = sync_timeframe(tf)
        
    # 2. Propagate
    # We iterate again to propagate.
    # Order matters? User implies 1h is "Root".
    # But technically, if we run 30m and find success, we propagate to others.
    # The logic "check if already done" handles the "don't send back to 1h" part implicitly
    # because 1h success list should already contain them (since 1h ran first).
    
    for tf in TIMEFRAMES:
        if tf_successes[tf]:
            propagate_strategies(tf, tf_successes[tf])
            
    print("SYNC DONE.")

if __name__ == "__main__":
    main()
