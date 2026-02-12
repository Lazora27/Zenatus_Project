#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zenatus Candidate JSON Generator
Creates timeframe-specific candidate JSON files from existing strategy listings
"""

import json
import os
from pathlib import Path

BASE_PATH = Path("/opt/Zenatus_Dokumentation/Listing/Full_backtest")
OUTPUT_PATH = BASE_PATH

def generate_candidate_files():
    """Generate candidate JSON files for each timeframe"""
    
    timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    for timeframe in timeframes:
        tf_path = BASE_PATH / timeframe
        if not tf_path.exists():
            print(f"Timeframe directory not found: {tf_path}")
            continue
        
        # Load all strategy files
        all_strategies = set()
        
        status_files = {
            "working": tf_path / "indicators_working.json",
            "successful": tf_path / "indicators_succesful_backtested.json",
            "warning": tf_path / "indicators_warnings.json",
            "error": tf_path / "indicators_errors.json",
            "timeout": tf_path / "indicators_timeout.json",
            "no_results": tf_path / "indicators_no_results.json"
        }
        
        # Load strategies from each status file
        for status, file_path in status_files.items():
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        strategies = data.get("scripts", [])
                        all_strategies.update(strategies)
                        print(f"Loaded {len(strategies)} {status} strategies for {timeframe}")
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        # Create candidate file
        candidate_data = {
            "timeframe": timeframe,
            "generated_at": str(Path.cwd()),
            "strategies": sorted(list(all_strategies)),
            "total_count": len(all_strategies),
            "metadata": {
                "working": len(load_strategies_from_file(status_files["working"])),
                "successful": len(load_strategies_from_file(status_files["successful"])),
                "warning": len(load_strategies_from_file(status_files["warning"])),
                "error": len(load_strategies_from_file(status_files["error"])),
                "timeout": len(load_strategies_from_file(status_files["timeout"])),
                "no_results": len(load_strategies_from_file(status_files["no_results"]))
            }
        }
        
        output_file = tf_path / f"candidates_{timeframe}.json"
        
        try:
            with open(output_file, 'w') as f:
                json.dump(candidate_data, f, indent=2, ensure_ascii=False)
            print(f"Created {output_file} with {len(all_strategies)} total strategies")
        except Exception as e:
            print(f"Error writing {output_file}: {e}")

def load_strategies_from_file(file_path):
    """Load strategies from a JSON file"""
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data.get("scripts", [])
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def generate_status_specific_candidates():
    """Generate separate candidate files for each status"""
    
    timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    statuses = ["working", "successful", "warning", "error", "timeout", "no_results"]
    
    for timeframe in timeframes:
        tf_path = BASE_PATH / timeframe
        if not tf_path.exists():
            continue
        
        for status in statuses:
            source_file = tf_path / f"indicators_{status}s.json" if status != "successful" else tf_path / "indicators_succesful_backtested.json"
            
            if source_file.exists():
                strategies = load_strategies_from_file(source_file)
                
                if strategies:
                    candidate_data = {
                        "timeframe": timeframe,
                        "status": status,
                        "strategies": strategies,
                        "count": len(strategies),
                        "source_file": str(source_file)
                    }
                    
                    output_file = tf_path / f"candidates_{timeframe}_{status}.json"
                    
                    try:
                        with open(output_file, 'w') as f:
                            json.dump(candidate_data, f, indent=2, ensure_ascii=False)
                        print(f"Created {output_file} with {len(strategies)} {status} strategies")
                    except Exception as e:
                        print(f"Error writing {output_file}: {e}")

if __name__ == "__main__":
    print("Generating candidate JSON files...")
    generate_candidate_files()
    print("\nGenerating status-specific candidate files...")
    generate_status_specific_candidates()
    print("Done!")