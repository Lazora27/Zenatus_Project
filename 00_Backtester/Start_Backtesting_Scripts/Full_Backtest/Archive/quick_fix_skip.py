import json
from pathlib import Path

BASE = Path(r"/opt/Zenatus_Backtester")
SKIP_FILE = BASE / "Scripts" / "SKIP_LIST_CORRECT.json"

data = json.load(open(SKIP_FILE))
problematic = [372, 373, 374, 375, 376, 377]

data['stable_success'] = [i for i in data['stable_success'] if i not in problematic]
data['problem_indicators'] = sorted(set(data['problem_indicators']) | set(problematic))
data['skip_indicators'] = sorted(set(data['skip_indicators']) | set(problematic))
data['summary']['stable_success_count'] = len(data['stable_success'])
data['summary']['problem_count'] = len(data['problem_indicators'])
data['summary']['skip_total'] = len(data['skip_indicators'])

json.dump(data, open(SKIP_FILE, 'w'), indent=2)

print(f"Stable: {len(data['stable_success'])}")
print(f"Problem: {len(data['problem_indicators'])}")
print(f"SKIP: {len(data['skip_indicators'])}")
