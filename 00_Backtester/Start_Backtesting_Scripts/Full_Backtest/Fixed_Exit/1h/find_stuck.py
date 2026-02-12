import json
import os
from pathlib import Path

QUEUE_FILE = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_working.json")
RESULTS_DIR = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h")

def main():
    # 1. Load Queue
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        all_scripts = sorted(data.get("scripts", []))
        
    # 2. Get Done
    done = set()
    for f in RESULTS_DIR.glob("*.csv"):
        # File: 001_001_trend_sma_1h.csv
        # Strategy: 001_trend_sma
        parts = f.stem.split("_")
        # Reconstruct: parts[1:-1] joined by _? 
        # 001_trend_sma -> 001_001_trend_sma_1h
        # 054_trend_ultimate_osc -> 054_054_trend_ultimate_osc_1h
        
        # Robust match: find which script is contained in filename
        # Or simpler:
        # Script "001_trend_sma" -> Check if file "001_001_trend_sma_1h.csv" exists.
        pass

    # Better: Loop through all scripts and check if done
    stuck_list = []
    
    # Replicate Sharding Logic
    NUM_NODES = 10
    total = len(all_scripts)
    chunk_size = (total + NUM_NODES - 1) // NUM_NODES
    chunks = [all_scripts[i:i + chunk_size] for i in range(0, total, chunk_size)]
    
    print(f"Total: {total}, Chunk size: {chunk_size}")
    
    for i, chunk in enumerate(chunks):
        node_id = i + 1
        print(f"Node {node_id}: Checking {len(chunk)} strategies...")
        
        # Find first not done
        found_stuck = False
        for script in chunk:
            ind_num = int(script.split("_")[0])
            fname = f"{ind_num:03d}_{script}_1h.csv"
            fpath = RESULTS_DIR / fname
            
            if not fpath.exists():
                # This is the first unfinished one. It must be the one stuck.
                print(f"  -> STUCK? {script}")
                stuck_list.append(script)
                found_stuck = True
                break # Only the first one is blocking the queue
        
        if not found_stuck:
            print("  -> All done.")
            
    # Define file path
    blocked_file = Path("/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_blocked.json")
    
    # Load existing blocked if any
    existing_blocked = []
    if blocked_file.exists():
        with open(blocked_file, "r") as f:
            existing_blocked = json.load(f).get("blocked", [])
            
    # Add newly stuck ones to the list
    # But wait, find_stuck.py logic currently assumes that the first missing CSV is the stuck one.
    # If we already marked 002_trend_ema as blocked, we should skip it in the check?
    # Or better: We need to see if we made progress BEYOND the blocked ones.
    
    # Let's refine the logic:
    # 1. Load blocked list first.
    # 2. Iterate chunks.
    # 3. If a script is in blocked list, ignore it (assume it's skipped).
    # 4. If a script is NOT in blocked list and NO CSV exists -> This is the NEW stuck one.
    
    final_blocked = set(existing_blocked)
    
    for i, chunk in enumerate(chunks):
        node_id = i + 1
        print(f"Node {node_id}: Checking {len(chunk)} strategies...")
        
        found_stuck = False
        for script in chunk:
            if script in final_blocked:
                # We know this is blocked, so we expect no CSV. Skip check.
                continue
                
            ind_num = int(script.split("_")[0])
            fname = f"{ind_num:03d}_{script}_1h.csv"
            fpath = RESULTS_DIR / fname
            
            if not fpath.exists():
                # This is a NEW stuck one!
                print(f"  -> NEW STUCK: {script}")
                final_blocked.add(script)
                found_stuck = True
                break 
        
        if not found_stuck:
            print("  -> All unblocked strategies done.")
            
    sorted_blocked = sorted(list(final_blocked))
    
    with open(blocked_file, "w") as f:
        json.dump({"blocked": sorted_blocked}, f, indent=2)
        
    print(f"\nSaved {len(sorted_blocked)} blocked strategies to {blocked_file}")
    # print("Blocked strategies:", sorted_blocked)

if __name__ == "__main__":
    main()
