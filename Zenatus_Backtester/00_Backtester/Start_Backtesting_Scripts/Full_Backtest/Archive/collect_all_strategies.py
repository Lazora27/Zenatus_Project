import json
from pathlib import Path

# Pfade
unique_path = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
tested_path = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\Fixed_Exit\1h")
skip_list_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\SKIP_LIST_CORRECT.json")
results_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\BACKTEST_ANALYSE_RESULTS.json")
log_file = Path(r"/opt/Zenatus_Dokumentation\LOG\problem_fix_1h_20260131_035953.log")

print("="*80)
print("AUFGABE 1: SAMMLE ALLE STRATEGIEN")
print("="*80)
print()

# 1. Sammle alle 467 Unique Strategien
all_unique = []
for py_file in unique_path.glob("*.py"):
    if py_file.stem != "__pycache__":
        try:
            ind_num = int(py_file.stem.split('_')[0])
            name = '_'.join(py_file.stem.split('_')[1:])
            all_unique.append({
                'id': ind_num,
                'name': name,
                'filename': py_file.name
            })
        except:
            pass

all_unique = sorted(all_unique, key=lambda x: x['id'])

print(f"Gefunden: {len(all_unique)} Unique Strategien")
print(f"Range: {all_unique[0]['id']} - {all_unique[-1]['id']}")
print()

# 2. Sammle alle 218 getesteten Strategien
all_tested = []
for csv_file in tested_path.glob("*.csv"):
    if csv_file.stem != "__pycache__":
        try:
            parts = csv_file.stem.split('_')
            ind_num = int(parts[0])
            name = '_'.join(parts[2:])
            all_tested.append({
                'id': ind_num,
                'name': name,
                'filename': csv_file.name
            })
        except:
            pass

all_tested = sorted(all_tested, key=lambda x: x['id'])

print(f"Gefunden: {len(all_tested)} getestete Strategien")
print(f"Range: {all_tested[0]['id']} - {all_tested[-1]['id']}")
print()

# Erstelle JSON für Aufgabe 1
aufgabe1_data = {
    'total_unique': len(all_unique),
    'total_tested': len(all_tested),
    'unique_strategies': all_unique,
    'tested_strategies': all_tested
}

output_file1 = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\AUFGABE1_ALL_STRATEGIES.json")
with open(output_file1, 'w') as f:
    json.dump(aufgabe1_data, f, indent=2)

print(f"✅ Aufgabe 1 gespeichert: {output_file1}")
print()

# AUFGABE 2: Differenz finden
print("="*80)
print("AUFGABE 2: DIFFERENZ FINDEN")
print("="*80)
print()

unique_ids = set([s['id'] for s in all_unique])
tested_ids = set([s['id'] for s in all_tested])

not_tested_ids = unique_ids - tested_ids
not_tested = [s for s in all_unique if s['id'] in not_tested_ids]
not_tested = sorted(not_tested, key=lambda x: x['id'])

print(f"Unique Strategien: {len(unique_ids)}")
print(f"Getestete Strategien: {len(tested_ids)}")
print(f"Noch nicht getestet: {len(not_tested_ids)}")
print()

# Zeige erste 20
print("Erste 20 nicht getestete:")
for s in not_tested[:20]:
    print(f"  Ind#{s['id']:03d}: {s['name']}")
print()

# AUFGABE 3: Status kategorisieren
print("="*80)
print("AUFGABE 3: STATUS KATEGORISIEREN")
print("="*80)
print()

# Lade SKIP_LIST und Results
with open(skip_list_file, 'r') as f:
    skip_data = json.load(f)

with open(results_file, 'r') as f:
    results = json.load(f)

# Lade Log für Fehler/Warnings
log_content = ""
if log_file.exists():
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        log_content = f.read()

# Kategorisiere
categorized = {
    'A_fehlerhaft': [],
    'B_timeout': [],
    'C_no_results': [],
    'D_warnings': [],
    'E_backtestfaehig': []
}

skip_indicators = set(skip_data['skip_indicators'])
problem_indicators = set(skip_data['problem_indicators'])
stable_success = set(skip_data['stable_success'])
already_tested = set(skip_data['already_tested'])

# Timeout und No Results aus aktuellem Backtest
timeout_ids = set([int(k) for k in results['timeout_details'].keys()])
no_results_ids = set(results['no_results_ids'])
error_ids = set(results['error_ids'])

for strategy in not_tested:
    ind_id = strategy['id']
    
    # A: Fehlerhaft
    if ind_id in error_ids:
        categorized['A_fehlerhaft'].append({
            **strategy,
            'reason': 'Error in current backtest'
        })
    # B: Timeout
    elif ind_id in timeout_ids:
        timeouts = results['timeout_details'].get(str(ind_id), 0)
        categorized['B_timeout'].append({
            **strategy,
            'timeouts': timeouts,
            'reason': f'{timeouts} timeout warnings'
        })
    # C: No Results
    elif ind_id in no_results_ids:
        categorized['C_no_results'].append({
            **strategy,
            'reason': 'No results in current backtest'
        })
    # D: Warnings (in problem_indicators aber nicht error/timeout/no_results)
    elif ind_id in problem_indicators:
        categorized['D_warnings'].append({
            **strategy,
            'reason': 'Listed in problem indicators'
        })
    # E: Backtestfähig
    else:
        categorized['E_backtestfaehig'].append({
            **strategy,
            'reason': 'No known issues - ready for backtest'
        })

print("KATEGORISIERUNG:")
print(f"A - Fehlerhaft: {len(categorized['A_fehlerhaft'])}")
print(f"B - Timeout: {len(categorized['B_timeout'])}")
print(f"C - No Results: {len(categorized['C_no_results'])}")
print(f"D - Warnings: {len(categorized['D_warnings'])}")
print(f"E - Backtestfähig: {len(categorized['E_backtestfaehig'])}")
print()

# AUFGABE 4: Finale Status-JSON
print("="*80)
print("AUFGABE 4: FINALE STATUS-JSON")
print("="*80)
print()

aufgabe4_data = {
    'summary': {
        'total_unique': len(all_unique),
        'total_tested': len(all_tested),
        'total_not_tested': len(not_tested),
        'A_fehlerhaft': len(categorized['A_fehlerhaft']),
        'B_timeout': len(categorized['B_timeout']),
        'C_no_results': len(categorized['C_no_results']),
        'D_warnings': len(categorized['D_warnings']),
        'E_backtestfaehig': len(categorized['E_backtestfaehig'])
    },
    'not_tested_strategies': not_tested,
    'categorized': categorized
}

output_file4 = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\AUFGABE4_STATUS_KATEGORISIERUNG.json")
with open(output_file4, 'w') as f:
    json.dump(aufgabe4_data, f, indent=2)

print(f"✅ Aufgabe 4 gespeichert: {output_file4}")
print()

# Zusammenfassung
print("="*80)
print("ZUSAMMENFASSUNG ALLER AUFGABEN")
print("="*80)
print()
print(f"✅ Aufgabe 1: {len(all_unique)} Unique + {len(all_tested)} Getestete")
print(f"✅ Aufgabe 2: {len(not_tested)} noch nicht getestet")
print(f"✅ Aufgabe 3: Kategorisiert in A-E")
print(f"✅ Aufgabe 4: Status-JSON erstellt")
print()
print("DATEIEN:")
print(f"  - AUFGABE1_ALL_STRATEGIES.json")
print(f"  - AUFGABE4_STATUS_KATEGORISIERUNG.json")
