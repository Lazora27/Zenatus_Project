"""Erstelle separate JSONs für ERROR/TIMEOUT/FEW/FAILED"""
import json
from pathlib import Path

base = Path(r"/opt/Zenatus_Backtester\01_Backtest_System")

# Lade EXTREME Results
extreme = json.load(open(base / 'EXTREME_TIMEOUT_10MIN_RESULTS.json'))

# Lade FIXED JSON (mit Float->Int Fix)
fixed_json = json.load(open(base / 'Scripts' / 'INDICATORS_PROBLEMSOLVING_FIXED.json'))

# 1. ERROR_106
error_ids = extreme['ERROR_SIGNALS']
error_json = {str(k): v for k, v in fixed_json.items() if int(k) in error_ids}
json.dump(error_json, open(base / 'Scripts' / 'QUICKTEST_ERROR_106.json', 'w'), indent=2)
print(f"ERROR_106: {len(error_json)} indicators")

# 2. TIMEOUT_9
timeout_ids = extreme['TIMEOUT_SIGNALS']
timeout_json = {str(k): v for k, v in fixed_json.items() if int(k) in timeout_ids}
json.dump(timeout_json, open(base / 'Scripts' / 'QUICKTEST_TIMEOUT_9.json', 'w'), indent=2)
print(f"TIMEOUT_9: {len(timeout_json)} indicators")

# 3. FEW_8
few_ids = extreme['FEW_SIGNALS']
few_json = {str(k): v for k, v in fixed_json.items() if int(k) in few_ids}
json.dump(few_json, open(base / 'Scripts' / 'QUICKTEST_FEW_8.json', 'w'), indent=2)
print(f"FEW_8: {len(few_json)} indicators")

# 4. FAILED_1
failed_ids = extreme['FAILED']
failed_json = {str(k): v for k, v in fixed_json.items() if int(k) in failed_ids}
json.dump(failed_json, open(base / 'Scripts' / 'QUICKTEST_FAILED_1.json', 'w'), indent=2)
print(f"FAILED_1: {len(failed_json)} indicators")

print(f"\nTOTAL: {len(error_json) + len(timeout_json) + len(few_json) + len(failed_json)} indicators")
