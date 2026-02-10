"""
DEEP-ANALYSE: Jeder Indikator einzeln
Extrahiere ALLE Parameter + bestimme optimale Ranges
Ziel: ~500 Kombinationen pro Symbol
"""
import re
import ast
import json
from pathlib import Path
from collections import defaultdict

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")

def extract_parameter_details(code: str, filename: str) -> dict:
    """Extrahiere ALLE Parameter mit Details aus Code"""
    
    params = {}
    
    # 1. Suche nach PARAMETERS Dictionary
    if 'PARAMETERS' in code:
        try:
            params_match = re.search(r'PARAMETERS\s*=\s*\{(.+?)\n\s*\}', code, re.DOTALL)
            if params_match:
                params_block = params_match.group(1)
                
                # Extrahiere jeden Parameter
                param_pattern = r"['\"](\w+)['\"]\s*:\s*\{([^}]+)\}"
                for match in re.finditer(param_pattern, params_block):
                    param_name = match.group(1)
                    param_config = match.group(2)
                    
                    # Ignoriere tp_pips, sl_pips, ml_feature
                    if param_name in ['tp_pips', 'sl_pips', 'ml_feature', 'optimize', 'description']:
                        continue
                    
                    # Extrahiere min, max, default, values
                    min_val = None
                    max_val = None
                    default_val = None
                    values = None
                    
                    min_match = re.search(r"['\"]min['\"]\s*:\s*(\d+)", param_config)
                    if min_match:
                        min_val = int(min_match.group(1))
                    
                    max_match = re.search(r"['\"]max['\"]\s*:\s*(\d+)", param_config)
                    if max_match:
                        max_val = int(max_match.group(1))
                    
                    default_match = re.search(r"['\"]default['\"]\s*:\s*(\d+\.?\d*)", param_config)
                    if default_match:
                        default_val = float(default_match.group(1))
                    
                    values_match = re.search(r"['\"]values['\"]\s*:\s*\[([^\]]+)\]", param_config)
                    if values_match:
                        values_str = values_match.group(1)
                        try:
                            values = [int(x.strip()) for x in values_str.split(',') if x.strip().isdigit()]
                        except:
                            pass
                    
                    if min_val or max_val or default_val or values:
                        params[param_name] = {
                            'min': min_val,
                            'max': max_val,
                            'default': default_val,
                            'values': values
                        }
        except Exception as e:
            pass
    
    # 2. Suche nach Parameter-Verwendung in generate_signals
    gen_signals_match = re.search(r'def\s+generate_signals[^(]*\(([^)]+)\)', code)
    if gen_signals_match:
        sig = gen_signals_match.group(1).lower()
        
        # Häufige Parameter
        common_params = ['period', 'fast_period', 'slow_period', 'signal_period', 
                        'window', 'length', 'lookback', 'threshold', 'k_period', 'd_period',
                        'deviation', 'multiplier', 'alpha', 'beta', 'vfactor']
        
        for param in common_params:
            if param in sig and param not in params:
                # Bestimme Default-Range basierend auf Parameter-Typ
                if 'period' in param or 'window' in param or 'length' in param or 'lookback' in param:
                    params[param] = {
                        'min': 5,
                        'max': 200,
                        'default': 20,
                        'values': None
                    }
                elif param in ['threshold']:
                    params[param] = {
                        'min': 10,
                        'max': 90,
                        'default': 50,
                        'values': None
                    }
                elif param in ['deviation', 'multiplier']:
                    params[param] = {
                        'min': 1.0,
                        'max': 3.0,
                        'default': 2.0,
                        'values': None
                    }
                elif param in ['alpha', 'beta', 'vfactor']:
                    params[param] = {
                        'min': 0.1,
                        'max': 1.0,
                        'default': 0.5,
                        'values': None
                    }
    
    # 3. Fallback: Wenn keine Parameter gefunden, nutze period
    if not params:
        params['period'] = {
            'min': 5,
            'max': 200,
            'default': 20,
            'values': None
        }
    
    return params

def calculate_optimal_ranges(params: dict, target_combos: int = 500) -> dict:
    """Berechne optimale Ranges um ~target_combos zu erreichen"""
    
    num_params = len(params)
    if num_params == 0:
        return {}
    
    # Ziel: combos_per_param ^ num_params ≈ target_combos
    # combos_per_param = target_combos ^ (1/num_params)
    combos_per_param = int(target_combos ** (1/num_params))
    combos_per_param = max(5, min(combos_per_param, 20))  # 5-20 Werte pro Parameter
    
    optimized_params = {}
    
    for param_name, param_config in params.items():
        if param_config.get('values'):
            # Nutze vorhandene values
            values = param_config['values']
            # Limitiere auf combos_per_param
            if len(values) > combos_per_param:
                step = len(values) // combos_per_param
                values = values[::step][:combos_per_param]
            optimized_params[param_name] = {
                'values': values,
                'range': {
                    'start': min(values),
                    'end': max(values),
                    'step': 'custom'
                }
            }
        else:
            # Generiere Range
            min_val = param_config.get('min', 5)
            max_val = param_config.get('max', 200)
            default_val = param_config.get('default', (min_val + max_val) / 2)
            
            # Berechne Step
            range_size = max_val - min_val
            step = max(1, range_size // (combos_per_param - 1))
            
            # Generiere Values
            values = []
            current = min_val
            while current <= max_val and len(values) < combos_per_param:
                values.append(current)
                current += step
            
            # Stelle sicher dass default und max enthalten sind
            if default_val not in values:
                values.append(int(default_val))
            if max_val not in values:
                values.append(max_val)
            
            values = sorted(set(values))[:combos_per_param]
            
            optimized_params[param_name] = {
                'values': values,
                'range': {
                    'start': min_val,
                    'end': max_val,
                    'step': step
                }
            }
    
    return optimized_params

# MAIN
print("="*80)
print("DEEP PARAMETER ANALYSE - JEDER INDIKATOR EINZELN")
print("="*80)

indicator_files = sorted(INDICATORS_PATH.glob("*.py"))
all_results = {}
stats = {
    'total': 0,
    'with_params': 0,
    'param_counts': defaultdict(int),
    'avg_combos': []
}

for ind_file in indicator_files:  # ALLE 467 Indikatoren
    try:
        ind_num = int(ind_file.stem.split('_')[0])
        ind_name = ind_file.stem
        
        with open(ind_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Extrahiere Parameter
        params = extract_parameter_details(code, ind_file.name)
        
        # Berechne optimale Ranges
        optimized = calculate_optimal_ranges(params, target_combos=500)
        
        # Berechne tatsächliche Kombinationen
        total_combos = 1
        for param_config in optimized.values():
            total_combos *= len(param_config['values'])
        
        all_results[ind_num] = {
            'name': ind_name,
            'parameters': optimized,
            'total_combinations': total_combos
        }
        
        stats['total'] += 1
        if params:
            stats['with_params'] += 1
        stats['param_counts'][len(params)] += 1
        stats['avg_combos'].append(total_combos)
        
        print(f"\n#{ind_num:03d} {ind_name}")
        print(f"  Parameter: {len(params)}")
        for param_name, param_config in optimized.items():
            values = param_config['values']
            range_info = param_config['range']
            print(f"    {param_name}: {len(values)} values ({range_info['start']} - {range_info['end']}, step={range_info['step']})")
        print(f"  Total Kombinationen: {total_combos}")
        
    except Exception as e:
        print(f"❌ {ind_file.name}: {str(e)[:80]}")

print(f"\n{'='*80}")
print("STATISTIK:")
print(f"  Analysiert: {stats['total']}")
print(f"  Mit Parametern: {stats['with_params']}")
print(f"  Durchschnittliche Kombinationen: {sum(stats['avg_combos'])/len(stats['avg_combos']):.0f}")
print(f"\n  Parameter-Verteilung:")
for count, num_inds in sorted(stats['param_counts'].items()):
    print(f"    {count} Parameter: {num_inds} Indikatoren")

print(f"\n{'='*80}")
print("SAMPLE ABGESCHLOSSEN")
print(f"{'='*80}")

# Speichere Sample
output_file = Path("DEEP_PARAMETER_ANALYSIS_SAMPLE.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print(f"\n✅ Sample gespeichert: {output_file}")
