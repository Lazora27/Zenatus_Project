# -*- coding: utf-8 -*-
import json
import subprocess
import sys
import time
import os
from pathlib import Path

# CONFIG
BASE_PATH = Path(os.environ.get("ZENATUS_BASE_PATH", r"/opt/Zenatus_Backtester"))
WORKER_SCRIPT = BASE_PATH / "00_Backtester" / "Start_Backtesting_Scripts" / "Full_Backtest" / "Fixed_Exit" / "1h" / "FULL_BACKTEST_1H_WORKER.py"
QUEUE_FILE = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_working.json")
BLOCKED_FILE = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_blocked.json")
RESULTS_DIR = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h")
LOG_DIR = Path(r"/opt/Zenatus_Dokumentation/LOG/1h/nodes")

def get_existing_strategies():
    if not RESULTS_DIR.exists():
        return set()
    return set() # Placeholder, logic is in main

def main():
    print("=== 10-NODE CLUSTER LAUNCHER (RESUME MODE + SKIP BLOCKED) ===")
    
    # 1. Load Queue
    if not QUEUE_FILE.exists():
        print("Queue file not found!")
        return
        
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        all_scripts = sorted(data.get("scripts", [])) # Sort to ensure consistent order
        
    total_initial = len(all_scripts)
    if total_initial == 0:
        print("Queue is empty.")
        return

    # 2. Load Blocked
    blocked = set()
    if BLOCKED_FILE.exists():
        with open(BLOCKED_FILE, "r") as f:
            blocked = set(json.load(f).get("blocked", []))
            print(f"Loaded {len(blocked)} blocked strategies.")

    # 3. Filter existing and blocked
    scripts_to_run = []
    for s in all_scripts:
        if s in blocked:
            continue
            
        # Construct expected filename
        try:
            ind_num = int(s.split("_")[0])
            fname = f"{ind_num:03d}_{s}_1h.csv"
            fpath = RESULTS_DIR / fname
            if not fpath.exists():
                scripts_to_run.append(s)
        except:
            # If name format is weird, include it just in case
            scripts_to_run.append(s)
            
    total_remaining = len(scripts_to_run)
    print(f"Total in Queue: {total_initial}")
    print(f"Blocked:        {len(blocked)}")
    print(f"Already Done:   {total_initial - total_remaining - len(blocked)}")
    print(f"Remaining:      {total_remaining}")
    
    if total_remaining == 0:
        print("All strategies completed! Nothing to run.")
        return
        
    # 4. Split into 10 chunks
    NUM_NODES = 10
    chunk_size = (total_remaining + NUM_NODES - 1) // NUM_NODES
    chunks = [scripts_to_run[i:i + chunk_size] for i in range(0, total_remaining, chunk_size)]
    
    print(f"Launching {len(chunks)} nodes with ~{chunk_size} tasks each...")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    procs = []
    
    for i, chunk in enumerate(chunks):
        node_id = i + 1
        scripts_arg = ",".join(chunk)
        
        log_out = LOG_DIR / f"node_{node_id}.stdout.log"
        log_err = LOG_DIR / f"node_{node_id}.stderr.log"
        
        cmd = [
            sys.executable, "-u",
            str(WORKER_SCRIPT),
            "--worker-id", str(node_id),
            "--scripts", scripts_arg
        ]
        
        print(f"  -> Launching Node {node_id} ({len(chunk)} tasks)")
        
        # Open logs
        f_out = open(log_out, "w")
        f_err = open(log_err, "w")
        
        p = subprocess.Popen(cmd, stdout=f_out, stderr=f_err)
        procs.append(p)
        
    print(f"All {len(procs)} nodes launched.")
    print(f"Monitor logs at: {LOG_DIR}")
    
    # Optional: Wait for all to finish?
    # Or just exit and let them run in background?
    # User asked for "launcher", implies fire and forget or monitor.
    # Let's wait and print status periodically.
    
    try:
        while True:
            alive = [p.poll() is None for p in procs].count(True)
            if alive == 0:
                print("All nodes finished.")
                break
            print(f"Nodes running: {alive}/{NUM_NODES}...", end="\r")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nLauncher stopping (nodes continue running)...")

if __name__ == "__main__":
    main()
