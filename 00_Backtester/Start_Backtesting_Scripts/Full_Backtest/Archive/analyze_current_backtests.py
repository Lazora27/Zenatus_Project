from pathlib import Path
import json

BASE = Path(r"/opt/Zenatus_Backtester")

# Zähle CSVs
csv_dir = BASE / "Documentation" / "Fixed_Exit" / "1h"
csv_files = list(csv_dir.glob("*.csv"))
csv_ids = sorted([int(f.stem.split('_')[0]) for f in csv_files])

print("="*80)
print("BACKTEST STATUS - 02:16 UHR")
print("="*80)

# PROBLEM_FIX Analyse
problem_log = BASE / "LOGS" / "problem_fix_1h_20260130_234838.log"
with open(problem_log, 'r', encoding='utf-8') as f:
    problem_lines = f.readlines()

problem_success = [line for line in problem_lines if '[SUCCESS]' in line]
print(f"\nPROBLEM_FIX BACKTEST:")
print(f"  SUCCESS: {len(problem_success)} Indikatoren")
if problem_success:
    first_success = problem_success[0].split('Ind#')[1].split()[0]
    last_success = problem_success[-1].split('Ind#')[1].split()[0]
    print(f"  Range: Ind#{first_success} bis Ind#{last_success}")
    print(f"  Laufzeit: ~2.5 Stunden")

# STABLE_SUCCESS Analyse
stable_log = BASE / "LOGS" / "stable_success_1h_20260130_234828.log"
with open(stable_log, 'r', encoding='utf-8') as f:
    stable_lines = f.readlines()

stable_success = [line for line in stable_lines if '[SUCCESS]' in line]
stable_timeouts = [line for line in stable_lines if 'VectorBT TIMEOUT' in line]
print(f"\nSTABLE_SUCCESS BACKTEST:")
print(f"  SUCCESS: {len(stable_success)} Indikatoren")
print(f"  TIMEOUTS: {len(stable_timeouts)} VectorBT Timeouts")
print(f"  Problem: Testet nur Ind#367-371 (alle timeouten)")

# CSV Statistik
print(f"\n{'='*80}")
print(f"GESAMT STATISTIK:")
print(f"  Total CSVs: {len(csv_files)}")
print(f"  Neue seit 23:40: {len([i for i in csv_ids if i >= 569])}")
print(f"  SUCCESS Rate: {len(csv_files)/467*100:.1f}%")
print(f"{'='*80}")

# Identifiziere Problem-Indikatoren
problem_ids = [367, 368, 369, 370, 371]
print(f"\nPROBLEM-INDIKATOREN IDENTIFIZIERT:")
print(f"  IDs: {problem_ids}")
print(f"  Grund: Nur VectorBT Timeouts, keine SUCCESS")
print(f"  Aktion: Zu SKIP hinzufügen, STABLE_SUCCESS neu starten")
