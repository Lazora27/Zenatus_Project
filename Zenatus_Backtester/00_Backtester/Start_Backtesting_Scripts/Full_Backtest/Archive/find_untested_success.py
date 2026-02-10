"""Finde alle SUCCESS Indikatoren die noch NICHT getestet wurden"""
import json
from pathlib import Path

base = Path(r"/opt/Zenatus_Backtester\01_Backtest_System")

# Lade alle SUCCESS Listen
quicktest = json.load(open(base / 'QUICKTEST_RESULTS.json'))
extreme = json.load(open(base / 'EXTREME_TIMEOUT_10MIN_RESULTS.json'))
error3 = json.load(open(base / 'ERROR_3_RETEST_RESULTS.json'))

# Alle SUCCESS Indikatoren
success_original = set(quicktest['SUCCESS'])
success_extreme = set(extreme['SUCCESS'])
success_error3 = set(error3['SUCCESS'])
all_success = success_original | success_extreme | success_error3

print(f"ALLE SUCCESS INDIKATOREN:")
print(f"  Original QUICKTEST: {len(success_original)}")
print(f"  + EXTREME_TIMEOUT: {len(success_extreme)}")
print(f"  + ERROR_3_RETEST: {len(success_error3)}")
print(f"  TOTAL UNIQUE: {len(all_success)}")
print()

# Lade bereits getestete (bis 4 Uhr morgens + 92/89)
# SUCCESS_REMAINING.json enthält die 92/89 die getestet wurden
success_remaining = json.load(open(base / 'Scripts' / 'SUCCESS_REMAINING.json'))
tested_92 = set(success_remaining['remaining_success_indicators'])

# Finde welche noch NICHT getestet wurden
untested = all_success - tested_92

print(f"BEREITS GETESTET (bis 4 Uhr + 92/89): {len(tested_92)}")
print(f"NOCH NICHT GETESTET: {len(untested)}")
print()

if untested:
    print(f"UNGETESTETE SUCCESS IDs:")
    print(sorted(untested))
    print()
    
    # Speichere für nächsten Backtest
    result = {
        'untested_success_indicators': sorted(untested),
        'count': len(untested),
        'note': 'Diese SUCCESS Indikatoren wurden noch nicht mit Full Backtest getestet'
    }
    
    json.dump(result, open(base / 'Scripts' / 'UNTESTED_SUCCESS.json', 'w'), indent=2)
    print(f"Gespeichert in UNTESTED_SUCCESS.json")
else:
    print("ALLE SUCCESS Indikatoren wurden bereits getestet!")
