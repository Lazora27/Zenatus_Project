"""
Erstelle JSON für Problem-Indikatoren mit MAX 2 Kombinationen
Für schnelle Tests mit 15min Timeout
"""
import json
from pathlib import Path

BASE = Path(r"/opt/Zenatus_Backtester")
ANALYSIS_JSON = BASE.parent / "01_Backtest_System" / "Scripts" / "INDICATORS_COMPLETE_ANALYSIS.json"
SKIP_LIST = BASE / "Scripts" / "SKIP_LIST_CORRECT.json"

# Lade Problem-Indikatoren
skip_data = json.load(open(SKIP_LIST))
problem_inds = skip_data['problem_indicators']

print(f"Problem-Indikatoren: {len(problem_inds)}")

# Lade Analysis JSON für Parameter
analysis = json.load(open(ANALYSIS_JSON))

# Erstelle vereinfachte Configs mit MAX 2 Kombinationen
problem_configs = {}

for ind_id in problem_inds:
    ind_key = str(ind_id)
    if ind_key in analysis:
        config = analysis[ind_key]
        
        # Vereinfache Entry-Parameter: Nur 1 Wert pro Parameter
        entry_params = config.get('entry_parameters', {})
        simplified_entry = {}
        
        for param_name, param_config in entry_params.items():
            values = param_config.get('values', [])
            optimal = param_config.get('optimal', [])
            
            # Nimm optimal oder ersten Wert
            if optimal:
                simplified_entry[param_name] = {
                    'values': [optimal[0]],
                    'optimal': [optimal[0]]
                }
            elif values:
                simplified_entry[param_name] = {
                    'values': [values[0]],
                    'optimal': [values[0]]
                }
        
        # Vereinfache Exit-Parameter: Nur 2 TP/SL Kombinationen
        exit_params = config.get('exit_parameters', {})
        tp_values = exit_params.get('tp_pips', {}).get('values', [])
        sl_values = exit_params.get('sl_pips', {}).get('values', [])
        tp_optimal = exit_params.get('tp_pips', {}).get('optimal', [])
        sl_optimal = exit_params.get('sl_pips', {}).get('optimal', [])
        
        # Nimm 2 beste TP/SL Kombinationen
        if tp_optimal and sl_optimal:
            simplified_tp = tp_optimal[:2]
            simplified_sl = sl_optimal[:2]
        elif tp_values and sl_values:
            simplified_tp = tp_values[:2]
            simplified_sl = sl_values[:2]
        else:
            simplified_tp = [100]
            simplified_sl = [50]
        
        simplified_exit = {
            'tp_pips': {
                'values': simplified_tp,
                'optimal': simplified_tp
            },
            'sl_pips': {
                'values': simplified_sl,
                'optimal': simplified_sl
            }
        }
        
        # Erstelle vereinfachte Config
        problem_configs[ind_key] = {
            'indicator_type': config.get('indicator_type', 'unknown'),
            'entry_parameters': simplified_entry,
            'exit_parameters': simplified_exit,
            'note': 'Simplified for problem indicators - MAX 2 combinations'
        }
        
        # Berechne Kombinationen
        entry_combos = 1
        for param in simplified_entry.values():
            entry_combos *= len(param.get('values', [1]))
        
        tp_combos = len(simplified_tp)
        sl_combos = len(simplified_sl)
        total_combos = entry_combos * tp_combos * sl_combos
        
        print(f"Ind#{ind_id}: {entry_combos} entry × {tp_combos} TP × {sl_combos} SL = {total_combos} combos")

# Speichere
output_file = BASE / "Scripts" / "INDICATORS_PROBLEM_2COMBOS.json"
with open(output_file, 'w') as f:
    json.dump(problem_configs, f, indent=2)

print(f"\n✅ Gespeichert: {output_file}")
print(f"Total Problem-Indikatoren: {len(problem_configs)}")
print(f"Max Kombinationen pro Indikator: 2-4")
