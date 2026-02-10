import json
from pathlib import Path

BASE = Path(r"/opt/Zenatus_Backtester")
SKIP_FILE = BASE / "Scripts" / "SKIP_LIST_CORRECT.json"

data = json.load(open(SKIP_FILE))

# Füge 367-371 zu SKIP und PROBLEM hinzu
new_problem_ids = [367, 368, 369, 370, 371]

for ind_id in new_problem_ids:
    if ind_id not in data['skip_indicators']:
        data['skip_indicators'].append(ind_id)
    if ind_id not in data['problem_indicators']:
        data['problem_indicators'].append(ind_id)
    if ind_id in data['stable_success']:
        data['stable_success'].remove(ind_id)

data['skip_indicators'] = sorted(data['skip_indicators'])
data['problem_indicators'] = sorted(data['problem_indicators'])
data['stable_success'] = sorted(data['stable_success'])

data['summary']['skip_total'] = len(data['skip_indicators'])
data['summary']['problem_count'] = len(data['problem_indicators'])
data['summary']['stable_success_count'] = len(data['stable_success'])

json.dump(data, open(SKIP_FILE, 'w'), indent=2)

print(f"✅ SKIP-Liste aktualisiert:")
print(f"   Stable SUCCESS: {len(data['stable_success'])} (entfernt: 367-371)")
print(f"   Problem: {len(data['problem_indicators'])} (hinzugefügt: 367-371)")
print(f"   SKIP total: {len(data['skip_indicators'])}")
