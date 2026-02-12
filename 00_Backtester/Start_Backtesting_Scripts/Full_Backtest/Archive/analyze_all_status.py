"""Analysiere kompletten Status aller Backtests"""
from pathlib import Path
import re
import json

base = Path(r"/opt/Zenatus_Backtester\01_Backtest_System")

# 1. PRODUCTION_SUCCESS_92 Status
log_file = base / "LOGS" / "production_success_92_1h_20260130_123328.log"
if log_file.exists():
    log_text = log_file.read_text(encoding='utf-8')
    success_92 = len(re.findall(r'\[SUCCESS\] Ind#\d+', log_text))
    error_92 = len(re.findall(r'\[ERROR\] Ind#\d+', log_text))
    print(f"PRODUCTION_SUCCESS_92:")
    print(f"  SUCCESS: {success_92}/89")
    print(f"  ERROR: {error_92}")
    print(f"  Status: {'FERTIG' if success_92 + error_92 >= 89 else 'LÄUFT'}")
    print()

# 2. EXTREME_TIMEOUT_10MIN Results
extreme_file = base / "EXTREME_TIMEOUT_10MIN_RESULTS.json"
if extreme_file.exists():
    extreme = json.load(open(extreme_file))
    print(f"EXTREME_TIMEOUT_10MIN (157 Indikatoren):")
    print(f"  SUCCESS: {len(extreme['SUCCESS'])}")
    print(f"  ERROR_SIGNALS: {len(extreme['ERROR_SIGNALS'])}")
    print(f"  TIMEOUT_SIGNALS: {len(extreme['TIMEOUT_SIGNALS'])}")
    print(f"  FEW_SIGNALS: {len(extreme['FEW_SIGNALS'])}")
    print(f"  FAILED: {len(extreme['FAILED'])}")
    print()

# 3. ERROR_3_RETEST Results
error3_file = base / "ERROR_3_RETEST_RESULTS.json"
if error3_file.exists():
    error3 = json.load(open(error3_file))
    print(f"ERROR_3_RETEST (3 Indikatoren):")
    print(f"  SUCCESS: {len(error3['SUCCESS'])}/3")
    print()

# 4. Gesamtstatistik
quicktest_file = base / "QUICKTEST_RESULTS.json"
if quicktest_file.exists():
    quicktest = json.load(open(quicktest_file))
    total_success = len(quicktest.get('SUCCESS', []))
    
    # Addiere neue SUCCESS
    if extreme_file.exists():
        total_success += len(extreme['SUCCESS'])
    if error3_file.exists():
        total_success += len(error3['SUCCESS'])
    
    print(f"GESAMTSTATISTIK:")
    print(f"  Original SUCCESS: {len(quicktest.get('SUCCESS', []))}")
    print(f"  + EXTREME_TIMEOUT: {len(extreme['SUCCESS']) if extreme_file.exists() else 0}")
    print(f"  + ERROR_3_RETEST: {len(error3['SUCCESS']) if error3_file.exists() else 0}")
    print(f"  + PRODUCTION_SUCCESS_92: {success_92 if log_file.exists() else 0}")
    print(f"  TOTAL SUCCESS: ~{total_success}")
    print()

# 5. Nächste Schritte
print(f"NÄCHSTE SCHRITTE:")
print(f"  1. Warte auf PRODUCTION_SUCCESS_92 Completion")
print(f"  2. Erstelle QUICKTEST für 106 ERROR_SIGNALS (2 Combos)")
print(f"  3. Füge erfolgreiche Indikatoren zu Main Backtest hinzu")
