"""
Finale Korrektur der SKIP-Liste:
- Entferne 372-377 aus STABLE_SUCCESS (sind problematisch)
- Füge 372-377 zu SKIP_INDICATORS hinzu
- Füge 372-377 zu PROBLEM_INDICATORS hinzu (außer 374 ist bereits FAILED)
"""
import json
from pathlib import Path

BASE = Path(r"/opt/Zenatus_Backtester")
SKIP_FILE = BASE / "Scripts" / "SKIP_LIST_CORRECT.json"

# Lade aktuelle Daten
data = json.load(open(SKIP_FILE))

# IDs 372-377 sind problematisch (aus bisherigen Tests)
problematic_372_377 = [372, 373, 374, 375, 376, 377]

# Entferne aus STABLE_SUCCESS
stable_success = data['stable_success']
stable_success = [i for i in stable_success if i not in problematic_372_377]

# Füge zu PROBLEM hinzu (374 ist bereits drin als FAILED)
problem_inds = data['problem_indicators']
for ind_id in problematic_372_377:
    if ind_id not in problem_inds:
        problem_inds.append(ind_id)
problem_inds = sorted(problem_inds)

# Füge zu SKIP hinzu
skip_inds = data['skip_indicators']
for ind_id in problematic_372_377:
    if ind_id not in skip_inds:
        skip_inds.append(ind_id)
skip_inds = sorted(skip_inds)

# Update
data['stable_success'] = sorted(stable_success)
data['problem_indicators'] = problem_inds
data['skip_indicators'] = skip_inds
data['summary']['stable_success_count'] = len(stable_success)
data['summary']['problem_count'] = len(problem_inds)
data['summary']['skip_total'] = len(skip_inds)

# Speichere
with open(SKIP_FILE, 'w') as f:
    json.dump(data, f, indent=2)

print(f"✅ SKIP-Liste korrigiert:")
print(f"   Stable SUCCESS: {len(stable_success)} (entfernt: 372-377)")
print(f"   Problem: {len(problem_inds)} (hinzugefügt: 372-377)")
print(f"   SKIP total: {len(skip_inds)}")
print(f"\n   372-377 in SKIP: {[i for i in problematic_372_377 if i in skip_inds]}")
