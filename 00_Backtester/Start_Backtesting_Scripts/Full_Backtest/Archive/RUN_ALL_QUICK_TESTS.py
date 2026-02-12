# -*- coding: utf-8 -*-
"""
MASTER QUICK TEST LAUNCHER
===========================
Runs all 4 timeframe quick tests sequentially
Total time: ~30-45 minutes
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_PATH = Path(__file__).parent

TESTS = [
    ('1H', 'QUICK_TEST_1H_PRODUCTION.py', '5-8 min'),
    ('30M', 'QUICK_TEST_30M_PRODUCTION.py', '6-10 min'),
    ('15M', 'QUICK_TEST_15M_PRODUCTION.py', '8-12 min'),
    ('5M', 'QUICK_TEST_5M_PRODUCTION.py', '10-15 min'),
]

print("="*80)
print("MASTER QUICK TEST LAUNCHER - ALL 4 TIMEFRAMES")
print("="*80)
print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
print(f"Expected total time: ~30-45 minutes\n")

results = []

for i, (tf, script, time_est) in enumerate(TESTS, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/4] STARTING: {tf} Quick Test (est. {time_est})")
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
            timeout=1800  # 30 min timeout per test
        )
        
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        
        if result.returncode == 0:
            results.append((tf, 'SUCCESS', f'{elapsed:.1f}min'))
            print(f"\n[{i}/4] {tf} COMPLETE! ({elapsed:.1f}min)")
        else:
            results.append((tf, 'FAILED', f'Exit code {result.returncode}'))
            print(f"\n[{i}/4] {tf} FAILED!")
            
    except subprocess.TimeoutExpired:
        results.append((tf, 'TIMEOUT', '30min+'))
        print(f"\n[{i}/4] {tf} TIMEOUT (exceeded 30min)")
    except Exception as e:
        results.append((tf, 'ERROR', str(e)[:50]))
        print(f"\n[{i}/4] {tf} ERROR: {e}")

print("\n" + "="*80)
print("ALL TESTS COMPLETE!")
print("="*80)
print(f"End: {datetime.now().strftime('%H:%M:%S')}\n")

print("SUMMARY:")
for tf, status, detail in results:
    symbol = "✓" if status == 'SUCCESS' else "✗"
    print(f"  {symbol} {tf:4s}: {status:8s} ({detail})")

print("\n" + "="*80)
print("Results saved in:")
print("  01_Backtest_System/Documentation/Quick_Test/[1h|30m|15m|5m]/")
print("="*80)
