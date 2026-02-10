"""
DEEP-ANALYSE: Indikatoren 301-320
FOKUS: Start/Step/End Werte für Entry-Parameter
Ziel: 500 (1-2 Param), 1000 (3-4 Param), 1500-2500 (5+ Param)
"""
import re
import json
from pathlib import Path

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
JSON_FILE = Path("INDICATORS_COMPLETE_ANALYSIS.json")

def analyze_indicator_deep(ind_file: Path) -> dict:
    """Deep-Analyse mit Fokus auf präzise Start/Step/End Werte"""
    
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
    
    class_match = re.search(r'class\s+(\w+)', code)
    if class_match:
        result['class_name'] = class_match.group(1)
    
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
    
    methods = re.findall(r'def\s+(\w+)\s*\(', code)
    result['methods'] = list(set(methods))
    
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
    
    if not result['parameters']:
        gen_signals_match = re.search(r'def\s+generate_signals[^(]*\(([^)]+)\)', code)
        if gen_signals_match:
            sig = gen_signals_match.group(1).lower()
            if 'period' in sig:
                result['parameters']['period'] = {'min': 5, 'max': 200, 'default': 20, 'values': None}
    
    num_params = len(result['parameters'])
    
    if num_params == 0:
        result['optimal_inputs']['period'] = {
            'start': 5,
            'end': 200,
            'step': 13,
            'values': [5, 18, 31, 44, 57, 70, 83, 96, 109, 122, 135, 148, 161, 174, 187, 200],
            'count': 16
        }
        result['optimal_inputs']['tp_pips'] = {'values': [30, 50, 75, 110], 'count': 4}
        result['optimal_inputs']['sl_pips'] = {'values': [20, 30, 45, 70], 'count': 4}
        result['calculated_combinations'] = 16 * 4 * 4
        result['target_combinations'] = 500
        
    elif num_params == 1:
        result['target_combinations'] = 500
        param_name = list(result['parameters'].keys())[0]
        param_config = result['parameters'][param_name]
        
        start = int(param_config['min'] or 5)
        end = int(param_config['max'] or 200)
        
        if param_config['values']:
            values = param_config['values'][:16]
            step = int((end - start) / (len(values) - 1)) if len(values) > 1 else 1
        else:
            num_values = 16
            step = int((end - start) / (num_values - 1))
            values = [start + i * step for i in range(num_values)]
        
        result['optimal_inputs'][param_name] = {
            'start': start,
            'end': end,
            'step': step,
            'values': values,
            'count': len(values)
        }
        result['optimal_inputs']['tp_pips'] = {'values': [30, 50, 75, 110], 'count': 4}
        result['optimal_inputs']['sl_pips'] = {'values': [20, 30, 45, 70], 'count': 4}
        result['calculated_combinations'] = len(values) * 4 * 4
        
    elif num_params == 2:
        result['target_combinations'] = 500
        param_names = list(result['parameters'].keys())
        
        for param_name in param_names:
            param_config = result['parameters'][param_name]
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            
            if param_config['values']:
                values = param_config['values'][:8]
                step = int((end - start) / (len(values) - 1)) if len(values) > 1 else 1
            else:
                num_values = 8
                step = int((end - start) / (num_values - 1))
                values = [start + i * step for i in range(num_values)]
            
            result['optimal_inputs'][param_name] = {
                'start': start,
                'end': end,
                'step': step,
                'values': values,
                'count': len(values)
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [35, 60, 100], 'count': 3}
        result['optimal_inputs']['sl_pips'] = {'values': [25, 45, 75], 'count': 3}
        result['calculated_combinations'] = 8 * 8 * 3 * 3
        
    elif num_params == 3:
        result['target_combinations'] = 1000
        param_names = list(result['parameters'].keys())
        
        for param_name in param_names:
            param_config = result['parameters'][param_name]
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            
            if param_config['values']:
                values = param_config['values'][:6]
                step = int((end - start) / (len(values) - 1)) if len(values) > 1 else 1
            else:
                num_values = 6
                step = int((end - start) / (num_values - 1))
                values = [start + i * step for i in range(num_values)]
            
            result['optimal_inputs'][param_name] = {
                'start': start,
                'end': end,
                'step': step,
                'values': values,
                'count': len(values)
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [40, 75], 'count': 2}
        result['optimal_inputs']['sl_pips'] = {'values': [30, 60], 'count': 2}
        result['calculated_combinations'] = 6 * 6 * 6 * 2 * 2
        
    elif num_params == 4:
        result['target_combinations'] = 1000
        param_names = list(result['parameters'].keys())
        
        for param_name in param_names:
            param_config = result['parameters'][param_name]
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            
            if param_config['values']:
                values = param_config['values'][:5]
                step = int((end - start) / (len(values) - 1)) if len(values) > 1 else 1
            else:
                num_values = 5
                step = int((end - start) / (num_values - 1))
                values = [start + i * step for i in range(num_values)]
            
            result['optimal_inputs'][param_name] = {
                'start': start,
                'end': end,
                'step': step,
                'values': values,
                'count': len(values)
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [50, 100], 'count': 2}
        result['optimal_inputs']['sl_pips'] = {'values': [35, 70], 'count': 2}
        result['calculated_combinations'] = (5 ** 4) * 2 * 2
        
    else:
        result['target_combinations'] = 2000
        values_per_param = 4
        
        for param_name, param_config in result['parameters'].items():
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            
            if param_config['values']:
                values = param_config['values'][:values_per_param]
                step = int((end - start) / (len(values) - 1)) if len(values) > 1 else 1
            else:
                step = int((end - start) / (values_per_param - 1)) if values_per_param > 1 else 1
                values = [start + i * step for i in range(values_per_param)]
            
            result['optimal_inputs'][param_name] = {
                'start': start,
                'end': end,
                'step': step,
                'values': values,
                'count': len(values)
            }
        
        result['optimal_inputs']['tp_pips'] = {'values': [50, 100], 'count': 2}
        result['optimal_inputs']['sl_pips'] = {'values': [35, 70], 'count': 2}
        result['calculated_combinations'] = (values_per_param ** num_params) * 2 * 2
    
    return result

print("="*80)
print("DEEP-ANALYSE: INDIKATOREN 301-320")
print("="*80)

if JSON_FILE.exists():
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
else:
    all_results = {}

for i in range(301, 321):
    ind_files = list(INDICATORS_PATH.glob(f"{i:03d}_*.py"))
    
    if not ind_files:
        print(f"\n❌ Indikator #{i:03d} nicht gefunden")
        continue
    
    ind_file = ind_files[0]
    result = analyze_indicator_deep(ind_file)
    
    print(f"\n{'='*80}")
    print(f"#{i:03d}: {ind_file.stem}")
    print(f"Klasse: {result['class_name']}, Parameter: {len(result['parameters'])}")
    
    print(f"ENTRY-PARAMETER:")
    for param_name, param_config in result['optimal_inputs'].items():
        if param_name not in ['tp_pips', 'sl_pips']:
            print(f"  {param_name}: Start={param_config.get('start')}, End={param_config.get('end')}, Step={param_config.get('step')}, Count={param_config['count']}")
    print(f"Kombinationen: {result['calculated_combinations']}")
    
    all_results[str(i)] = result

with open(JSON_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print(f"✅ Analyse gespeichert")
print(f"{'='*80}")

new_count = sum(1 for k in all_results.keys() if 301 <= int(k) <= 320)
compatible = sum(1 for k, r in all_results.items() if 301 <= int(k) <= 320 and r['backtest_compatible'])
avg_combos = sum(r['calculated_combinations'] for k, r in all_results.items() if 301 <= int(k) <= 320) / new_count if new_count > 0 else 0

print(f"\n📊 STATISTIK (301-320): {new_count}/20 analysiert, {compatible} kompatibel, Ø {avg_combos:.0f} Kombinationen")
print(f"📊 GESAMT (1-320): {len(all_results)} Indikatoren")
