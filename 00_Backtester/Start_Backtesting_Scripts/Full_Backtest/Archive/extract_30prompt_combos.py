import json
from pathlib import Path

# Lade 30-Prompt JSON
json_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\INDICATORS_PROBLEM_2COMBOS.json")

with open(json_file, 'r') as f:
    data = json.load(f)

print("="*80)
print("EXTRAHIERE TP/SL KOMBINATIONEN AUS 30-PROMPT JSON")
print("="*80)
print()

# Analysiere alle Indikatoren
all_combos = {}
unique_combos = set()

for ind_id, config in data.items():
    exit_params = config.get('exit_parameters', {})
    tp_values = exit_params.get('tp_pips', {}).get('values', [])
    sl_values = exit_params.get('sl_pips', {}).get('values', [])
    
    if tp_values and sl_values:
        # Erstelle alle Kombinationen
        combos = []
        for tp in tp_values:
            for sl in sl_values:
                combos.append((tp, sl))
                unique_combos.add((tp, sl))
        
        all_combos[int(ind_id)] = combos

print(f"Indikatoren mit Configs: {len(all_combos)}")
print(f"Unique TP/SL Kombinationen: {len(unique_combos)}")
print()

# Zeige unique Kombinationen
print("Unique TP/SL Kombinationen:")
for combo in sorted(unique_combos):
    print(f"  TP={combo[0]}, SL={combo[1]}")
print()

# Zeige erste 10 Indikatoren
print("Erste 10 Indikatoren mit Configs:")
for ind_id in sorted(all_combos.keys())[:10]:
    combos = all_combos[ind_id]
    print(f"  Ind#{ind_id:03d}: {len(combos)} Kombos - {combos}")
print()

# Speichere
output = {
    'summary': {
        'total_indicators': len(all_combos),
        'unique_combos': len(unique_combos)
    },
    'indicator_combos': {str(k): v for k, v in all_combos.items()},
    'unique_combos': sorted(list(unique_combos))
}

output_file = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\EXTRACTED_30PROMPT_COMBOS.json")
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Gespeichert: {output_file}")
