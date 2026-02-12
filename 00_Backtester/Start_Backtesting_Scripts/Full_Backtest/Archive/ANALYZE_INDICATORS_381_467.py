"""
DEEP-ANALYSE: Indikatoren 381-467 (FINALE BATCH)
FOKUS: Start/Step/End Werte für Entry-Parameter
Ziel: 500 (1-2 Param), 1000 (3-4 Param), 1500-2500 (5+ Param)
"""
import re
import json
from pathlib import Path

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
JSON_FILE = Path("INDICATORS_COMPLETE_ANALYSIS.json")

def analyze_indicator_deep(ind_file: Path) -> dict:
    with open(ind_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    result = {
        'file': ind_file.name,
        'class_name': None,
        'class_structure': None,
        'parameters': {},
        'optimal_inputs': {},
        'backtest_compatible': True,
        'calculated_combinations': 256
    }
    
    class_match = re.search(r'class\s+(\w+)', code)
    if class_match:
        result['class_name'] = class_match.group(1)
    
    result['class_structure'] = 'VectorBT_Compatible' if 'generate_signals_fixed' in code else 'Standard'
    result['backtest_compatible'] = 'generate_signals_fixed' in code
    
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
                    
                    min_match = re.search(r"['\"]min['\"]\s*:\s*(\d+\.?\d*)", param_config)
                    if min_match:
                        min_val = float(min_match.group(1))
                    
                    max_match = re.search(r"['\"]max['\"]\s*:\s*(\d+\.?\d*)", param_config)
                    if max_match:
                        max_val = float(max_match.group(1))
                    
                    result['parameters'][param_name] = {'min': min_val, 'max': max_val}
        except:
            pass
    
    if not result['parameters']:
        if 'period' in code.lower():
            result['parameters']['period'] = {'min': 5, 'max': 200}
    
    num_params = len(result['parameters'])
    
    if num_params == 0:
        result['optimal_inputs']['period'] = {
            'start': 5, 'end': 200, 'step': 13, 'count': 16
        }
        result['optimal_inputs']['tp_pips'] = {'count': 4}
        result['optimal_inputs']['sl_pips'] = {'count': 4}
        result['calculated_combinations'] = 256
        
    elif num_params == 1:
        param_name = list(result['parameters'].keys())[0]
        param_config = result['parameters'][param_name]
        start = int(param_config['min'] or 5)
        end = int(param_config['max'] or 200)
        step = int((end - start) / 15)
        
        result['optimal_inputs'][param_name] = {
            'start': start, 'end': end, 'step': step, 'count': 16
        }
        result['optimal_inputs']['tp_pips'] = {'count': 4}
        result['optimal_inputs']['sl_pips'] = {'count': 4}
        result['calculated_combinations'] = 256
        
    elif num_params == 2:
        for param_name in result['parameters'].keys():
            param_config = result['parameters'][param_name]
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            step = int((end - start) / 7)
            
            result['optimal_inputs'][param_name] = {
                'start': start, 'end': end, 'step': step, 'count': 8
            }
        
        result['optimal_inputs']['tp_pips'] = {'count': 3}
        result['optimal_inputs']['sl_pips'] = {'count': 3}
        result['calculated_combinations'] = 576
        
    elif num_params == 3:
        for param_name in result['parameters'].keys():
            param_config = result['parameters'][param_name]
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            step = int((end - start) / 5)
            
            result['optimal_inputs'][param_name] = {
                'start': start, 'end': end, 'step': step, 'count': 6
            }
        
        result['optimal_inputs']['tp_pips'] = {'count': 2}
        result['optimal_inputs']['sl_pips'] = {'count': 2}
        result['calculated_combinations'] = 864
        
    else:
        for param_name in result['parameters'].keys():
            param_config = result['parameters'][param_name]
            start = int(param_config['min'] or 5)
            end = int(param_config['max'] or 100)
            step = int((end - start) / 4)
            
            result['optimal_inputs'][param_name] = {
                'start': start, 'end': end, 'step': step, 'count': 5
            }
        
        result['optimal_inputs']['tp_pips'] = {'count': 2}
        result['optimal_inputs']['sl_pips'] = {'count': 2}
        result['calculated_combinations'] = (5 ** num_params) * 4
    
    return result

print("="*80)
print("FINALE DEEP-ANALYSE: INDIKATOREN 381-467")
print("="*80)

if JSON_FILE.exists():
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
else:
    all_results = {}

for i in range(381, 468):
    ind_files = list(INDICATORS_PATH.glob(f"{i:03d}_*.py"))
    
    if not ind_files:
        print(f"❌ #{i:03d}")
        continue
    
    ind_file = ind_files[0]
    result = analyze_indicator_deep(ind_file)
    
    print(f"#{i:03d}: {result['class_name']}, P:{len(result['parameters'])}, K:{result['calculated_combinations']}")
    
    all_results[str(i)] = result

with open(JSON_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print(f"✅ FINALE ANALYSE ABGESCHLOSSEN!")
print(f"{'='*80}")

new_count = sum(1 for k in all_results.keys() if 381 <= int(k) <= 467)
avg = sum(r['calculated_combinations'] for k, r in all_results.items() if 381 <= int(k) <= 467) / new_count if new_count > 0 else 0
print(f"📊 (381-467): {new_count}/87, Ø {avg:.0f} Kombinationen")
print(f"📊 GESAMT (1-467): {len(all_results)} Indikatoren")
print(f"📊 Coverage: {len(all_results)/467*100:.1f}%")
