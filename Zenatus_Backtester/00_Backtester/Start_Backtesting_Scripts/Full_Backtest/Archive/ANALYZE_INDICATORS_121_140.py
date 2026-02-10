"""
DEEP-ANALYSE: Indikatoren 121-140
Erweitert gemeinsame JSON-Dokumentation
Ziel: 500 (1-2 Param), 1000 (3-4 Param), 1500-2500 (5+ Param)
"""
import re
import json
from pathlib import Path

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
JSON_FILE = Path("INDICATORS_COMPLETE_ANALYSIS.json")

def analyze_indicator_deep(ind_file: Path) -> dict:
    """Deep-Analyse mit dynamischem Kombinationen-Ziel"""
    
    with open(ind_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    result = {
        'file': ind_file.name,
        'class_name': None,
        'class_structure': None,
        'parameters': {},
        'methods': [],
        'optimal_inputs': {},
        'target_combinations': 500,
        'backtest_compatible': True,
        'notes': []
    }
    
    # 1. Finde Klassen-Name
    class_match = re.search(r'class\s+(\w+)', code)
    if class_match:
        result['class_name'] = class_match.group(1)
    
    # 2. Prüfe Klassen-Struktur
    if 'generate_signals_fixed' in code:
        result['class_structure'] = 'VectorBT_Compatible'
    elif 'generate_signals' in code:
        result['class_structure'] = 'Standard'
        result['backtest_compatible'] = False
        result['notes'].append('Needs generate_signals_fixed method')
    else:
        result['class_structure'] = 'Unknown'
        result['backtest_compatible'] = False
        result['notes'].append('No signal generation method found')
    
    # 3. Extrahiere Methoden
    methods = re.findall(r'def\s+(\w+)\s*\(', code)
    result['methods'] = list(set(methods))
    
    # 4. Extrahiere PARAMETERS Dictionary
    if 'PARAMETERS' in code:
        try:
            params_match = re.search(r'PARAMETERS\s*=\s*\{(.+?)\n\s*\}', code, re.DOTALL)
            if params_match:
                params_block = params_match.group(1)
                param_pattern = r"['\"](\w+)['\"]\s*:\s*\{([^}]+)\}"
                
                for match in re.finditer(param_pattern, params_block):
                    param_name = match.group(1)
                    param_config = match.group(2)
                    
                    if param_name in ['tp_pips', 'sl_pips', 'ml_feature', 'optimize', 'description']:
                        continue
                    
                    min_val = None
                    max_val = None
                    default_val = None
                    values = None
                    
                    min_match = re.search(r"['\"]min['\"]\s*:\s*(\d+\.?\d*)", param_config)
                    if min_match:
                        min_val = float(min_match.group(1))
                    
                    max_match = re.search(r"['\"]max['\"]\s*:\s*(\d+\.?\d*)", param_config)
                    if max_match:
                        max_val = float(max_match.group(1))
                    
                    default_match = re.search(r"['\"]default['\"]\s*:\s*(\d+\.?\d*)", param_config)
                    if default_match:
                        default_val = float(default_match.group(1))
                    
                    values_match = re.search(r"['\"]values['\"]\s*:\s*\[([^\]]+)\]", param_config)
                    if values_match:
                        values_str = values_match.group(1)
                        try:
                            values = [float(x.strip()) for x in values_str.split(',') if x.strip().replace('.','').replace('-','').isdigit()]
                        except:
                            pass
                    
                    result['parameters'][param_name] = {
                        'min': min_val,
                        'max': max_val,
                        'default': default_val,
                        'values': values
                    }
        except Exception as e:
            result['notes'].append(f'Error parsing PARAMETERS: {str(e)[:50]}')
    
    # 5. Fallback
    if not result['parameters']:
        gen_signals_match = re.search(r'def\s+generate_signals[^(]*\(([^)]+)\)', code)
        if gen_signals_match:
            sig = gen_signals_match.group(1).lower()
            if 'period' in sig:
                result['parameters']['period'] = {'min': 5, 'max': 200, 'default': 20, 'values': None}
    
    # 6. Berechne optimale Inputs
    num_params = len(result['parameters'])
    
    if num_params == 0:
        result['optimal_inputs']['period'] = {
            'values': [5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 90, 110, 130, 150, 175, 200],
            'count': 16,
            'range': {'start': 5, 'end': 200, 'step': 'variable'}
        }
        result['optimal_inputs']['tp_pips'] = {'values': [30, 40, 50, 65, 80, 100], 'count': 6}
        result['optimal_inputs']['sl_pips'] = {'values': [20, 25, 30, 40, 50, 65], 'count': 6}
        result['calculated_combinations'] = 576
        result['target_combinations'] = 500
        
    elif num_params == 1:
        result['target_combinations'] = 500
        param_name = list(result['parameters'].keys())[0]
        param_config = result['parameters'][param_name]
        
        min_val = param_config['min'] or 5
        max_val = param_config['max'] or 200
        
        if param_config['values']:
            values = param_config['values'][:16]
        else:
            step = (max_val - min_val) / 15
            values = [int(min_val + i * step) for i in range(16)]
        
        result['optimal_inputs'][param_name] = {
            'values': values,
            'count': len(values),
            'range': {'start': min_val, 'end': max_val, 'step': 'optimized'}
        }
        result['optimal_inputs']['tp_pips'] = {'values': [30, 40, 50, 65, 80, 100], 'count': 6}
        result['optimal_inputs']['sl_pips'] = {'values': [20, 25, 30, 40, 50, 65], 'count': 6}
        result['calculated_combinations'] = len(values) * 6 * 6
        
    elif num_params == 2:
        result['target_combinations'] = 500
        param_names = list(result['parameters'].keys())
        
        for param_name in param_names:
            param_config = result['parameters'][param_name]
            min_val = param_config['min'] or 5
            max_val = param_config['max'] or 100
            
            if param_config['values']:
                values = param_config['values'][:8]
            else:
                step = (max_val - min_val) / 7
                values = [int(min_val + i * step) for i in range(8)]
            
            result['optimal_inputs'][param_name] = {
                'values': values,
                'count': len(values),
                'range': {'start': min_val, 'end': max_val, 'step': 'optimized'}
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [35, 50, 75, 110], 'count': 4}
        result['optimal_inputs']['sl_pips'] = {'values': [22, 30, 45, 70], 'count': 4}
        result['calculated_combinations'] = 8 * 8 * 4 * 4
        
    elif num_params == 3:
        result['target_combinations'] = 1000
        param_names = list(result['parameters'].keys())
        
        for param_name in param_names:
            param_config = result['parameters'][param_name]
            min_val = param_config['min'] or 5
            max_val = param_config['max'] or 100
            
            if param_config['values']:
                values = param_config['values'][:5]
            else:
                step = (max_val - min_val) / 4
                values = [int(min_val + i * step) for i in range(5)]
            
            result['optimal_inputs'][param_name] = {
                'values': values,
                'count': len(values),
                'range': {'start': min_val, 'end': max_val, 'step': 'optimized'}
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [35, 50, 75, 110], 'count': 4}
        result['optimal_inputs']['sl_pips'] = {'values': [22, 30, 45, 70], 'count': 4}
        result['calculated_combinations'] = 5 * 5 * 5 * 4 * 4
        
    elif num_params == 4:
        result['target_combinations'] = 1000
        param_names = list(result['parameters'].keys())
        
        for param_name in param_names:
            param_config = result['parameters'][param_name]
            min_val = param_config['min'] or 5
            max_val = param_config['max'] or 100
            
            if param_config['values']:
                values = param_config['values'][:4]
            else:
                step = (max_val - min_val) / 3
                values = [int(min_val + i * step) for i in range(4)]
            
            result['optimal_inputs'][param_name] = {
                'values': values,
                'count': len(values),
                'range': {'start': min_val, 'end': max_val, 'step': 'optimized'}
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [40, 60, 90], 'count': 3}
        result['optimal_inputs']['sl_pips'] = {'values': [25, 40, 60], 'count': 3}
        result['calculated_combinations'] = (4 ** 4) * 3 * 3
        
    else:
        result['target_combinations'] = 2000
        values_per_param = 3
        
        for param_name, param_config in result['parameters'].items():
            min_val = param_config['min'] or 5
            max_val = param_config['max'] or 100
            
            if param_config['values']:
                values = param_config['values'][:values_per_param]
            else:
                step = (max_val - min_val) / (values_per_param - 1) if values_per_param > 1 else 0
                values = [int(min_val + i * step) for i in range(values_per_param)]
            
            result['optimal_inputs'][param_name] = {
                'values': values,
                'count': len(values),
                'range': {'start': min_val, 'end': max_val, 'step': 'optimized'}
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [35, 50, 75, 110], 'count': 4}
        result['optimal_inputs']['sl_pips'] = {'values': [22, 30, 45, 70], 'count': 4}
        result['calculated_combinations'] = (values_per_param ** num_params) * 4 * 4
    
    return result

# MAIN
print("="*80)
print("DEEP-ANALYSE: INDIKATOREN 121-140")
print("="*80)

# Lade existierende Daten
if JSON_FILE.exists():
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
else:
    all_results = {}

for i in range(121, 141):
    ind_files = list(INDICATORS_PATH.glob(f"{i:03d}_*.py"))
    
    if not ind_files:
        print(f"\n❌ Indikator #{i:03d} nicht gefunden")
        continue
    
    ind_file = ind_files[0]
    ind_num = i
    ind_name = ind_file.stem
    
    print(f"\n{'='*80}")
    print(f"#{ind_num:03d}: {ind_name}")
    print(f"{'='*80}")
    
    result = analyze_indicator_deep(ind_file)
    
    num_params = len(result['parameters'])
    
    print(f"Klasse: {result['class_name']}")
    print(f"Struktur: {result['class_structure']}")
    print(f"Backtest-Kompatibel: {result['backtest_compatible']}")
    print(f"Parameter: {num_params}")
    
    for param_name, param_config in result['parameters'].items():
        print(f"  - {param_name}: min={param_config['min']}, max={param_config['max']}, default={param_config['default']}")
    
    print(f"\nOptimale Inputs (Ziel: {result['target_combinations']} Kombinationen):")
    for param_name, param_config in result['optimal_inputs'].items():
        if param_name not in ['tp_pips', 'sl_pips']:
            print(f"  - {param_name}: {param_config['count']} Werte ({param_config.get('range', {}).get('start', 'N/A')} - {param_config.get('range', {}).get('end', 'N/A')})")
    
    print(f"  - TP: {result['optimal_inputs']['tp_pips']['count']} Werte")
    print(f"  - SL: {result['optimal_inputs']['sl_pips']['count']} Werte")
    print(f"\nBerechnete Kombinationen: {result['calculated_combinations']}")
    
    if result['notes']:
        print(f"\nHinweise:")
        for note in result['notes']:
            print(f"  ⚠️  {note}")
    
    all_results[str(ind_num)] = result

# Speichere erweiterte JSON
with open(JSON_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print(f"✅ Erweiterte Analyse gespeichert: {JSON_FILE}")
print(f"{'='*80}")

# Statistik
new_count = sum(1 for k in all_results.keys() if 121 <= int(k) <= 140)
compatible = sum(1 for k, r in all_results.items() if 121 <= int(k) <= 140 and r['backtest_compatible'])
avg_combos = sum(r['calculated_combinations'] for k, r in all_results.items() if 121 <= int(k) <= 140) / new_count if new_count > 0 else 0

print(f"\n📊 STATISTIK (121-140):")
print(f"  Analysiert: {new_count}/20")
print(f"  Backtest-Kompatibel: {compatible}/{new_count}")
print(f"  Durchschnitt Kombinationen: {avg_combos:.0f}")

print(f"\n📊 GESAMT-STATISTIK (1-140):")
print(f"  Total Indikatoren: {len(all_results)}")
total_avg = sum(r['calculated_combinations'] for r in all_results.values()) / len(all_results) if all_results else 0
print(f"  Durchschnitt Kombinationen: {total_avg:.0f}")
