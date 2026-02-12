"""
Erstelle korrekte SKIP-Liste für STABLE_SUCCESS Backtest:
- Bereits getestete CSVs (117)
- Problem-Indikatoren (ERROR, TIMEOUT, FEW, FAILED)
"""
import json
from pathlib import Path

BASE = Path(r"/opt/Zenatus_Backtester")
CSV_DIR = BASE.parent / "01_Backtest_System" / "Documentation" / "Fixed_Exit" / "1h"

# 1. Bereits getestete CSVs
already_tested = sorted([int(f.stem.split('_')[0]) for f in CSV_DIR.glob('*.csv')])
print(f"Bereits getestete CSVs: {len(already_tested)}")

# 2. Lade alle Problem-Indikatoren
problem_inds = set()

# QUICKTEST_RESULTS
qt_file = BASE / "QUICKTEST_RESULTS.json"
if qt_file.exists():
    qt = json.load(open(qt_file))
    for key, value in qt.items():
        if key in ['TIMEOUT', 'TIMEOUT_SIGNALS', 'ERROR_SIGNALS', 'FEW_SIGNALS', 'FAILED']:
            if isinstance(value, list):
                problem_inds.update(value)

# EXTREME_TIMEOUT_10MIN_RESULTS
ext_file = BASE / "EXTREME_TIMEOUT_10MIN_RESULTS.json"
if ext_file.exists():
    ext = json.load(open(ext_file))
    for ind_id, result in ext.items():
        if ind_id.isdigit():
            status = result.get('status', '')
            if status in ['ERROR_SIGNALS', 'TIMEOUT_SIGNALS', 'FEW_SIGNALS', 'FAILED']:
                problem_inds.add(int(ind_id))

# ERROR_3_RETEST_RESULTS
err3_file = BASE / "ERROR_3_RETEST_RESULTS.json"
if err3_file.exists():
    err3 = json.load(open(err3_file))
    for ind_id, result in err3.items():
        if ind_id.isdigit():
            status = result.get('status', '')
            if status in ['ERROR_SIGNALS', 'TIMEOUT_SIGNALS', 'FEW_SIGNALS', 'FAILED']:
                problem_inds.add(int(ind_id))

problem_inds = sorted(problem_inds)
print(f"Problem-Indikatoren: {len(problem_inds)}")

# 3. Kombiniere
skip_list = sorted(set(already_tested) | set(problem_inds) | set([8]) | set(range(378, 397)) | set(range(467, 601)))
print(f"Total SKIP: {len(skip_list)}")

# 4. Berechne STABLE_SUCCESS (sollten getestet werden)
all_inds = set(range(1, 467))
stable_success = sorted(all_inds - set(skip_list))
print(f"\nSTABLE_SUCCESS (zu testen): {len(stable_success)}")
print(f"Erste 30 IDs: {stable_success[:30]}")

# 5. Speichere
output = {
    "skip_indicators": skip_list,
    "stable_success": stable_success,
    "already_tested": already_tested,
    "problem_indicators": problem_inds,
    "summary": {
        "skip_total": len(skip_list),
        "stable_success_count": len(stable_success),
        "already_tested_count": len(already_tested),
        "problem_count": len(problem_inds)
    }
}

output_file = BASE / "Scripts" / "SKIP_LIST_CORRECT.json"
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Gespeichert: {output_file}")
print(f"\nPython-Code für SKIP_INDICATORS:")
print(f"SKIP_INDICATORS = {skip_list}")
