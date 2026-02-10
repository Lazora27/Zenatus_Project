# -*- coding: utf-8 -*-
"""
MASTER FULL BACKTEST LAUNCHER
==============================
Runs all 4 timeframes sequentially
Total time: ~200-300 hours (8-12 days!)
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_PATH = Path(__file__).parent

TESTS = [
    ('1H', 'FULL_BACKTEST_1H_PRODUCTION.py', '40-60h'),
    ('30M', 'FULL_BACKTEST_30M_PRODUCTION.py', '50-70h'),
    ('15M', 'FULL_BACKTEST_15M_PRODUCTION.py', '60-80h'),
    ('5M', 'FULL_BACKTEST_5M_PRODUCTION.py', '70-90h'),
]

print("="*80)
print("MASTER FULL BACKTEST LAUNCHER - ALL 4 TIMEFRAMES")
print("="*80)
print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Expected total time: 200-300 hours (8-12 DAYS!)")
print(f"\n⚠️  WARNING: This will run for over a week!")
print(f"⚠️  Make sure your PC can stay on that long!\n")

input("Press ENTER to continue or CTRL+C to cancel...")

results = []

for i, (tf, script, time_est) in enumerate(TESTS, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/4] STARTING: {tf} Full Backtest (est. {time_est})")
    print(f"{'='*80}\n")
    
    script_path = SCRIPTS_PATH / script
    
    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        results.append((tf, 'FAILED', 'Script not found'))
        continue
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            text=True,
            timeout=None  # No timeout
        )
        
        elapsed = (datetime.now() - start_time).total_seconds() / 3600  # hours
        
        if result.returncode == 0:
            results.append((tf, 'SUCCESS', f'{elapsed:.1f}h'))
            print(f"\n[{i}/4] {tf} COMPLETE! ({elapsed:.1f}h)")
        else:
            results.append((tf, 'FAILED', f'Exit code {result.returncode}'))
            print(f"\n[{i}/4] {tf} FAILED!")
            
    except Exception as e:
        results.append((tf, 'ERROR', str(e)[:50]))
        print(f"\n[{i}/4] {tf} ERROR: {e}")

print("\n" + "="*80)
print("ALL BACKTESTS COMPLETE!")
print("="*80)
print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print("SUMMARY:")
for tf, status, detail in results:
    symbol = "✓" if status == 'SUCCESS' else "✗"
    print(f"  {symbol} {tf:4s}: {status:8s} ({detail})")

print("\n" + "="*80)
print("Results saved in:")
print("  01_Backtest_System/Documentation/Fixed_Exit/[1h|30m|15m|5m]/")
print("="*80)
