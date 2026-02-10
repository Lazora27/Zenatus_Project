# -*- coding: utf-8 -*-
"""
LAZORA MASTER LAUNCHER
======================
Runs all 4 timeframes: 1H -> 30M -> 15M -> 5M
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_PATH = Path(__file__).parent

TESTS = [
    ('1H', 'LAZORA_PHASE1_1H.py', '5min'),
    ('30M', 'LAZORA_PHASE1_30M.py', '10min'),
    ('15M', 'LAZORA_PHASE1_15M.py', '20min'),
    ('5M', 'LAZORA_PHASE1_5M.py', '20min'),
]

print("="*80)
print("LAZORA PHASE 1 - MASTER LAUNCHER")
print("="*80)
print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nOrder: 1H -> 30M -> 15M -> 5M")
print(f"Method: Sobol Sequence (500 samples per indicator)")
print(f"Features: Walk-Forward 80/20, Checkpoint, Heatmap Data\n")

input("Press ENTER to start...")

results = []

for i, (tf, script, timeout) in enumerate(TESTS, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/4] STARTING: {tf} ({timeout} timeout)")
    print(f"{'='*80}\n")
    
    script_path = SCRIPTS_PATH / script
    
    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        results.append((tf, 'FAILED', 'Not found'))
        continue
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            text=True,
            timeout=None
        )
        
        elapsed = (datetime.now() - start_time).total_seconds() / 3600
        
        if result.returncode == 0:
            results.append((tf, 'SUCCESS', f'{elapsed:.1f}h'))
            print(f"\n[{i}/4] {tf} COMPLETE! ({elapsed:.1f}h)")
        else:
            results.append((tf, 'FAILED', f'Exit {result.returncode}'))
            print(f"\n[{i}/4] {tf} FAILED!")
            
    except Exception as e:
        results.append((tf, 'ERROR', str(e)[:30]))
        print(f"\n[{i}/4] {tf} ERROR: {e}")

print("\n" + "="*80)
print("LAZORA PHASE 1 COMPLETE!")
print("="*80)
print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print("SUMMARY:")
for tf, status, detail in results:
    symbol = "OK" if status == 'SUCCESS' else "X"
    print(f"  [{symbol}] {tf:4s}: {status:8s} ({detail})")

print("\n" + "="*80)
print("Output:")
print("  CSV: 01_Backtest_System/Documentation/Fixed_Exit/[TF]/")
print("  Heatmap Data: 08_Heatmaps/Fixed_Exit/[TF]/")
print("  Checkpoints: 01_Backtest_System/CHECKPOINTS/")
print("="*80)
print("\nNext: Generate heatmaps with 03_HEATMAP_VISUALIZER.py")
