import json
from pathlib import Path

# Lade Status-Kategorisierung
status_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\AUFGABE4_STATUS_KATEGORISIERUNG.json")
skip_list_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\SKIP_LIST_CORRECT.json")

with open(status_file, 'r') as f:
    status_data = json.load(f)

with open(skip_list_file, 'r') as f:
    skip_data = json.load(f)

# Alle 252 nicht getesteten IDs
all_not_tested = [s['id'] for s in status_data['not_tested_strategies']]

# Problem-Indikatoren aus SKIP_LIST
problem_indicators = set(skip_data['problem_indicators'])

# Kategorisiere
problem_ids = [ind_id for ind_id in all_not_tested if ind_id in problem_indicators]
clean_ids = [ind_id for ind_id in all_not_tested if ind_id not in problem_indicators]

print("="*80)
print("KATEGORISIERUNG DER 252 NICHT GETESTETEN STRATEGIEN")
print("="*80)
print()
print(f"Total nicht getestet: {len(all_not_tested)}")
print(f"Problem-Strategien (in alter Problem-Liste): {len(problem_ids)}")
print(f"Nicht-Problem-Strategien (sauber): {len(clean_ids)}")
print()

# Speichere Listen
output = {
    'summary': {
        'total_not_tested': len(all_not_tested),
        'problem_count': len(problem_ids),
        'clean_count': len(clean_ids)
    },
    'problem_ids': sorted(problem_ids),
    'clean_ids': sorted(clean_ids)
}

output_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\PROBLEM_AND_CLEAN_IDS.json")
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Gespeichert: {output_file}")
print()
print("Problem-IDs (erste 20):")
for ind_id in sorted(problem_ids)[:20]:
    print(f"  {ind_id}")
print()
print("Clean-IDs (erste 20):")
for ind_id in sorted(clean_ids)[:20]:
    print(f"  {ind_id}")
