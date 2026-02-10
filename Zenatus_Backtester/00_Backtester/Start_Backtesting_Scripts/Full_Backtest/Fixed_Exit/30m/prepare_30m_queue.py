# -*- coding: utf-8 -*-
import json
import os
import sys
from pathlib import Path

# CONFIG
QC_REPORT = Path(r"/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h/QualityCheck/qc_report.txt")
BLOCKED_FILE_1H = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_blocked.json")
QUEUE_FILE_1H = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/1h/indicators_working.json")

# TARGET
QUEUE_FILE_30M = Path(r"/opt/Zenatus_Dokumentation/Listing/Full_backtest/30m/indicators_working.json")
QUEUE_FILE_30M.parent.mkdir(parents=True, exist_ok=True)

def main():
    print("=== FILTERING STRATEGIES FOR 30M ===")
    
    # 1. Load All Strategies (Base)
    if not QUEUE_FILE_1H.exists():
        print("Error: 1H Queue file not found.")
        return
        
    with open(QUEUE_FILE_1H, "r", encoding="utf-8") as f:
        data = json.load(f)
        all_strategies = set(data.get("scripts", []))
        
    print(f"Total Strategies (Base): {len(all_strategies)}")
    
    # 2. Load Blocked Strategies (1h)
    blocked = set()
    if BLOCKED_FILE_1H.exists():
        with open(BLOCKED_FILE_1H, "r") as f:
            blocked_data = json.load(f)
            blocked = set(blocked_data.get("blocked", []))
    print(f"Blocked (1h): {len(blocked)}")
    
    # 3. Load QC Failed Strategies
    qc_failed = set()
    if QC_REPORT.exists():
        with open(QC_REPORT, "r") as f:
            lines = f.readlines()
            # Basic parsing of the report structure
            # We look for lines ending in .csv and extract the strategy name
            # Filename format: 054_054_trend_ultimate_osc_1h.csv
            # Strategy name: 054_trend_ultimate_osc (usually)
            
            for line in lines:
                line = line.strip()
                if line.endswith(".csv"):
                    # Extract strategy name from filename
                    # Example: 054_054_trend_ultimate_osc_1h.csv
                    # The strategy name in queue is usually "054_trend_ultimate_osc"
                    
                    # Try to reconstruct strategy name
                    parts = line.replace(".csv", "").split("_")
                    # Remove last part (timeframe) -> 054_054_trend_ultimate_osc
                    # But wait, the queue names are like "054_trend_ultimate_osc"
                    # Let's check the queue format again.
                    
                    # Heuristic: Remove the timeframe suffix (_1h)
                    if line.endswith("_1h.csv"):
                        base = line.replace("_1h.csv", "")
                        # Often the filename has double number prefix? "054_054_..."
                        # Let's try to match against all_strategies
                        
                        # Case 1: Exact match (unlikely if filename has extra info)
                        if base in all_strategies:
                            qc_failed.add(base)
                            continue
                            
                        # Case 2: Double prefix "054_054_trend..." -> "054_trend..."
                        # Split by first underscore
                        if "_" in base:
                            # Try removing the first part if it duplicates the ID
                            # e.g. "054_054_trend" -> "054_trend"
                            potential_name = base.split("_", 1)[1]
                            if potential_name in all_strategies:
                                qc_failed.add(potential_name)
                                continue
                                
                            # Case 3: Just check if any strategy name is a substring
                            # This is risky but effective
                            found = False
                            for s in all_strategies:
                                if s in base:
                                    qc_failed.add(s)
                                    found = True
                                    break
                            if not found:
                                print(f"[WARN] Could not map QC file {line} to a strategy name.")
                                
    print(f"QC Failed: {len(qc_failed)}")
    
    # 4. Filter
    final_list = []
    excluded_count = 0
    
    for s in sorted(list(all_strategies)):
        if s in blocked:
            excluded_count += 1
            continue
        if s in qc_failed:
            excluded_count += 1
            continue
        final_list.append(s)
        
    print(f"Excluded: {excluded_count}")
    print(f"Final Count for 30m: {len(final_list)}")
    
    # 5. Save
    with open(QUEUE_FILE_30M, "w", encoding="utf-8") as f:
        json.dump({"scripts": final_list}, f, indent=4)
        
    print(f"Saved to {QUEUE_FILE_30M}")

if __name__ == "__main__":
    main()
