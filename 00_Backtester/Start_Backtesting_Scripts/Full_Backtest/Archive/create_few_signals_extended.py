"""Erstelle Extended Date Range JSON für FEW_SIGNALS Test"""
import json
from pathlib import Path

base = Path(r"/opt/Zenatus_Dokumentation\Dokumentation")

# Load FEW_SIGNALS IDs
targets = json.load(open(base / 'PROBLEMSOLVING_TARGETS.json'))
few_signals = targets['few_8']

# Load main JSON
main_json = json.load(open(base / 'INDICATORS_PROBLEMSOLVING_FIXED.json'))

# Create extended JSON with 2x date ranges
extended_json = {}
for ind_id in few_signals:
    if str(ind_id) in main_json:
        extended_json[str(ind_id)] = main_json[str(ind_id)].copy()

# Save
json.dump(extended_json, open(base / 'FEW_SIGNALS_EXTENDED.json', 'w'), indent=2)
print(f"Created FEW_SIGNALS_EXTENDED.json with {len(extended_json)} indicators")
print(f"IDs: {list(extended_json.keys())}")
