# -*- coding: utf-8 -*-
import json
import os
import sys
import subprocess
import time
from pathlib import Path

# CONFIG
QUEUE_FILE = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_working.json")
BLOCKED_FILE = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_blocked.json")
RESULTS_DIR = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h")
RUN_SCRIPT = Path(r"/opt/Zenatus_Backtester/00_Backtester/Start_Backtesting_Scripts/Full_Backtest/Fixed_Exit/1h/RUN_ALL_10_NODES.py")

def main():
    print("=== BLOCK CURRENT AND RESTART ===")
    
    # 1. Load Queue
    if not QUEUE_FILE.exists():
        print("Queue file not found!")
        return
        
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        all_scripts = sorted(data.get("scripts", []))
        
    # 2. Load Blocked
    blocked = set()
    if BLOCKED_FILE.exists():
        with open(BLOCKED_FILE, "r") as f:
            blocked_data = json.load(f)
            blocked = set(blocked_data.get("blocked", []))
            
    # 3. Filter existing and blocked
    scripts_to_run = []
    for s in all_scripts:
        if s in blocked:
            continue
            
        try:
            ind_num = int(s.split("_")[0])
            fname = f"{ind_num:03d}_{s}_1h.csv"
            fpath = RESULTS_DIR / fname
            if not fpath.exists():
                scripts_to_run.append(s)
        except:
            scripts_to_run.append(s)
            
    total_remaining = len(scripts_to_run)
    print(f"Total Remaining before blocking: {total_remaining}")
    
    if total_remaining == 0:
        print("Nothing to run or block.")
        return

    # 4. Identify Current Strategies (First of each chunk)
    NUM_NODES = 10
    chunk_size = (total_remaining + NUM_NODES - 1) // NUM_NODES
    chunks = [scripts_to_run[i:i + chunk_size] for i in range(0, total_remaining, chunk_size)]
    
    stuck_candidates = []
    for chunk in chunks:
        if chunk:
            stuck_candidates.append(chunk[0])
            
    print(f"Identified {len(stuck_candidates)} strategies to block (first of each chunk):")
    for s in stuck_candidates:
        print(f"  - {s}")
        blocked.add(s)
        
    # 5. Save Blocked
    with open(BLOCKED_FILE, "w") as f:
        json.dump({"blocked": sorted(list(blocked))}, f, indent=4)
    print("Blocked list updated.")
    
    # 6. Kill Processes
    print("Killing old processes...")
    subprocess.run(["pkill", "-f", "FULL_BACKTEST_1H_WORKER.py"])
    subprocess.run(["pkill", "-f", "RUN_ALL_10_NODES.py"])
    subprocess.run(["pkill", "-f", "monitor_nodes.py"])
    time.sleep(2)
    
if __name__ == "__main__":
    main()
