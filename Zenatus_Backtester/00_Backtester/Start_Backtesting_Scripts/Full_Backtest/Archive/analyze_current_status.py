"""
Analysiere aktuellen Status aller Indikatoren:
1. Bereits getestete (CSVs vorhanden)
2. STABLE_SUCCESS (aus bisherigen Tests, keine Fehler)
3. PROBLEM (Timeouts, Errors)
"""
import json
from pathlib import Path

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
CSV_DIR = BASE_PATH / "01_Backtest_System" / "Documentation" / "Fixed_Exit" / "1h"
ANALYSIS_JSON = BASE_PATH / "01_Backtest_System" / "Scripts" / "INDICATORS_COMPLETE_ANALYSIS.json"
QUICKTEST_RESULTS = BASE_PATH / "01_Backtest_System" / "QUICKTEST_RESULTS.json"
EXTREME_TIMEOUT = BASE_PATH / "01_Backtest_System" / "EXTREME_TIMEOUT_10MIN_RESULTS.json"
ERROR_3_RETEST = BASE_PATH / "01_Backtest_System" / "ERROR_3_RETEST_RESULTS.json"

# 1. Bereits getestete Indikatoren (CSVs vorhanden)
csv_files = list(CSV_DIR.glob("*.csv"))
already_tested = sorted([int(f.stem.split('_')[0]) for f in csv_files])

print(f"✅ BEREITS GETESTET (CSVs vorhanden): {len(already_tested)} Indikatoren")
print(f"   IDs: {already_tested[:10]}...{already_tested[-5:]}")

# 2. Lade alle bisherigen Test-Ergebnisse
all_success = set()
all_error = set()
all_timeout = set()
all_few = set()
all_failed = set()

# QUICKTEST_RESULTS
if QUICKTEST_RESULTS.exists():
    data = json.load(open(QUICKTEST_RESULTS))
    for ind_id, result in data.items():
        ind_num = int(ind_id)
        if result['status'] == 'SUCCESS':
            all_success.add(ind_num)
        elif result['status'] == 'ERROR_SIGNALS':
            all_error.add(ind_num)
        elif result['status'] == 'TIMEOUT_SIGNALS':
            all_timeout.add(ind_num)
        elif result['status'] == 'FEW_SIGNALS':
            all_few.add(ind_num)
        elif result['status'] == 'FAILED':
            all_failed.add(ind_num)

# EXTREME_TIMEOUT_10MIN_RESULTS
if EXTREME_TIMEOUT.exists():
    data = json.load(open(EXTREME_TIMEOUT))
    for ind_id, result in data.items():
        ind_num = int(ind_id)
        if result['status'] == 'SUCCESS':
            all_success.add(ind_num)
        elif result['status'] == 'ERROR_SIGNALS':
            all_error.add(ind_num)
        elif result['status'] == 'TIMEOUT_SIGNALS':
            all_timeout.add(ind_num)
        elif result['status'] == 'FEW_SIGNALS':
            all_few.add(ind_num)
        elif result['status'] == 'FAILED':
            all_failed.add(ind_num)

# ERROR_3_RETEST
if ERROR_3_RETEST.exists():
    data = json.load(open(ERROR_3_RETEST))
    for ind_id, result in data.items():
        ind_num = int(ind_id)
        if result['status'] == 'SUCCESS':
            all_success.add(ind_num)
            # Remove from error if now success
            all_error.discard(ind_num)

# 3. Kategorisiere
already_tested_set = set(already_tested)

# STABLE_SUCCESS: SUCCESS aber noch nicht getestet
stable_success = sorted(all_success - already_tested_set)

# PROBLEM: ERROR + TIMEOUT + FEW + FAILED
problem_inds = sorted(all_error | all_timeout | all_few | all_failed)

print(f"\n📊 KATEGORISIERUNG:")
print(f"   STABLE_SUCCESS (noch zu testen): {len(stable_success)} Indikatoren")
print(f"   PROBLEM (Errors/Timeouts): {len(problem_inds)} Indikatoren")
print(f"   Bereits getestet: {len(already_tested)} Indikatoren")
print(f"   TOTAL: {len(stable_success) + len(problem_inds) + len(already_tested)}")

# 4. Speichere Listen
output = {
    "already_tested": already_tested,
    "stable_success": stable_success,
    "problem_indicators": {
        "all": problem_inds,
        "error": sorted(all_error),
        "timeout": sorted(all_timeout),
        "few": sorted(all_few),
        "failed": sorted(all_failed)
    },
    "summary": {
        "already_tested_count": len(already_tested),
        "stable_success_count": len(stable_success),
        "problem_count": len(problem_inds),
        "total": len(stable_success) + len(problem_inds) + len(already_tested)
    }
}

output_file = BASE_PATH / "01_Backtest_System" / "Scripts" / "CURRENT_STATUS.json"
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Status gespeichert: {output_file}")

# 5. Details
print(f"\n📋 STABLE_SUCCESS IDs (erste 20):")
print(f"   {stable_success[:20]}")

print(f"\n⚠️ PROBLEM IDs (erste 20):")
print(f"   {problem_inds[:20]}")
