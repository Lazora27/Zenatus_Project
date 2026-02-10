import json
from pathlib import Path

BASE = Path(r"/opt/Zenatus_Backtester")
CSV_DIR = BASE.parent / "01_Backtest_System" / "Documentation" / "Fixed_Exit" / "1h"

# Bereits getestete CSVs
csvs = sorted([int(f.stem.split('_')[0]) for f in CSV_DIR.glob('*.csv')])
print(f"Already tested (CSVs): {len(csvs)}")

# Lade QUICKTEST_RESULTS
qt = json.load(open(BASE / "QUICKTEST_RESULTS.json"))
success = [int(k) for k,v in qt.items() if k.isdigit() and v.get('status')=='SUCCESS']
error = [int(k) for k,v in qt.items() if k.isdigit() and v.get('status')=='ERROR_SIGNALS']
timeout = [int(k) for k,v in qt.items() if k.isdigit() and v.get('status')=='TIMEOUT_SIGNALS']
few = [int(k) for k,v in qt.items() if k.isdigit() and v.get('status')=='FEW_SIGNALS']
failed = [int(k) for k,v in qt.items() if k.isdigit() and v.get('status')=='FAILED']

# Lade EXTREME_TIMEOUT
ext = json.load(open(BASE / "EXTREME_TIMEOUT_10MIN_RESULTS.json"))
success.extend([int(k) for k,v in ext.items() if k.isdigit() and v.get('status')=='SUCCESS'])
error.extend([int(k) for k,v in ext.items() if k.isdigit() and v.get('status')=='ERROR_SIGNALS'])
timeout.extend([int(k) for k,v in ext.items() if k.isdigit() and v.get('status')=='TIMEOUT_SIGNALS'])
few.extend([int(k) for k,v in ext.items() if k.isdigit() and v.get('status')=='FEW_SIGNALS'])
failed.extend([int(k) for k,v in ext.items() if k.isdigit() and v.get('status')=='FAILED'])

# Lade ERROR_3_RETEST
err3 = json.load(open(BASE / "ERROR_3_RETEST_RESULTS.json"))
for k,v in err3.items():
    if k.isdigit() and v.get('status')=='SUCCESS':
        success.append(int(k))
        if int(k) in error:
            error.remove(int(k))

# Dedupliziere
success = sorted(set(success))
error = sorted(set(error))
timeout = sorted(set(timeout))
few = sorted(set(few))
failed = sorted(set(failed))

# STABLE_SUCCESS = SUCCESS aber noch nicht getestet
stable = sorted(set(success) - set(csvs))
problem = sorted(set(error + timeout + few + failed))

print(f"STABLE_SUCCESS (to test): {len(stable)}")
print(f"PROBLEM (errors/timeouts): {len(problem)}")
print(f"\nStable IDs (first 30): {stable[:30]}")
print(f"Problem IDs (first 30): {problem[:30]}")

# Speichere
output = {
    "already_tested": csvs,
    "stable_success": stable,
    "problem": problem,
    "problem_details": {
        "error": error,
        "timeout": timeout,
        "few": few,
        "failed": failed
    }
}
json.dump(output, open(BASE / "Scripts" / "CURRENT_STATUS.json", 'w'), indent=2)
print(f"\nSaved to CURRENT_STATUS.json")
