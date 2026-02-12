# -*- coding: utf-8 -*-
"""
PRODUCTION MASTER LAUNCHER
==========================
Runs all 4 timeframes in order: 1H → 30M → 15M → 5M
With checkpoint resume capability
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_PATH = Path(__file__).parent

# CORRECT ORDER: Highest TF to Lowest TF
TESTS = [
    ('1H', 'PRODUCTION_1H_FINAL.py', '5min timeout'),
    ('30M', 'PRODUCTION_30M_FINAL.py', '10min timeout'),
    ('15M', 'PRODUCTION_15M_FINAL.py', '20min timeout'),
    ('5M', 'PRODUCTION_5M_FINAL.py', '20min timeout'),
]

print("="*80)
print("PRODUCTION MASTER LAUNCHER - ALL 4 TIMEFRAMES")
print("="*80)
print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nOrder: 1H → 30M → 15M → 5M (Highest to Lowest)")
print(f"\nFeatures:")
print(f"  - Walk-Forward 80/20")
print(f"  - Parameter Optimization (Period + TP/SL)")
print(f"  - Checkpoint Resume")
print(f"  - Live Progress Output")
print(f"  - Best Combo per Symbol\n")

input("Press ENTER to start or CTRL+C to cancel...")

results = []

for i, (tf, script, timeout_info) in enumerate(TESTS, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/4] STARTING: {tf} ({timeout_info})")
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
print("ALL TIMEFRAMES COMPLETE!")
print("="*80)
print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print("SUMMARY:")
for tf, status, detail in results:
    symbol = "✓" if status == 'SUCCESS' else "✗"
    print(f"  {symbol} {tf:4s}: {status:8s} ({detail})")

print("\n" + "="*80)
print("Results in: 01_Backtest_System/Documentation/Fixed_Exit/[TF]/")
print("Checkpoints in: 01_Backtest_System/CHECKPOINTS/")
print("="*80)
