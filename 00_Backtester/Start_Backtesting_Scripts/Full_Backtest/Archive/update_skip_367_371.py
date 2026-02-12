import json
from pathlib import Path

SKIP_FILE = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\SKIP_LIST_CORRECT.json")

data = json.load(open(SKIP_FILE))
new_ids = [367, 368, 369, 370, 371]

for i in new_ids:
    if i not in data['skip_indicators']:
        data['skip_indicators'].append(i)
    if i not in data['problem_indicators']:
        data['problem_indicators'].append(i)

data['stable_success'] = [i for i in data['stable_success'] if i not in new_ids]
data['skip_indicators'] = sorted(data['skip_indicators'])
data['problem_indicators'] = sorted(data['problem_indicators'])
data['stable_success'] = sorted(data['stable_success'])
data['summary']['skip_total'] = len(data['skip_indicators'])
data['summary']['problem_count'] = len(data['problem_indicators'])
data['summary']['stable_success_count'] = len(data['stable_success'])

json.dump(data, open(SKIP_FILE, 'w'), indent=2)

print(f"Stable: {len(data['stable_success'])}")
print(f"Problem: {len(data['problem_indicators'])}")
print(f"SKIP: {len(data['skip_indicators'])}")
