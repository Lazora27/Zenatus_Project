"""
Erstelle KORREKTE Configs: Entry-Parameter + TP/SL = ~500 Kombinationen
"""
import json
import re
from pathlib import Path
from collections import defaultdict

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")

def extract_parameters_from_code(code: str) -> dict:
    """Extrahiere Parameter aus PARAMETERS Dictionary"""
    params = {}
    
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
                    values = None
                    
                    min_match = re.search(r"['\"]min['\"]\s*:\s*(\d+)", param_config)
                    if min_match:
                        min_val = int(min_match.group(1))
                    
                    max_match = re.search(r"['\"]max['\"]\s*:\s*(\d+)", param_config)
                    if max_match:
                        max_val = int(max_match.group(1))
                    
                    values_match = re.search(r"['\"]values['\"]\s*:\s*\[([^\]]+)\]", param_config)
                    if values_match:
                        values_str = values_match.group(1)
                        try:
                            values = [int(x.strip()) for x in values_str.split(',') if x.strip().replace('-','').isdigit()]
                        except:
                            pass
                    
                    if min_val or max_val or values:
                        params[param_name] = {
                            'min': min_val or 5,
                            'max': max_val or 200,
                            'values': values
                        }
        except:
            pass
    
    if not params:
        params['period'] = {'min': 5, 'max': 200, 'values': None}
    
    return params

def calculate_optimal_distribution(params: dict, target_total: int = 500) -> tuple:
    """
    Berechne optimale Verteilung: Entry × TP × SL ≈ target_total
    
    Strategie:
    - Mehr Entry-Kombinationen wenn viele Parameter
    - Weniger Entry-Kombinationen wenn wenige Parameter
    - TP/SL füllt auf ~500 auf
    """
    num_params = len(params)
    
    if num_params == 1:
        # 1 Parameter: 20 Entry × 5 TP × 5 SL = 500
        entry_per_param = 20
        num_tp = 5
        num_sl = 5
    elif num_params == 2:
        # 2 Parameter: 10×10 Entry × 3 TP × 2 SL = 600
        entry_per_param = 10
        num_tp = 3
        num_sl = 2
    elif num_params == 3:
        # 3 Parameter: 5×5×5 Entry × 3 TP × 2 SL = 750
        entry_per_param = 5
        num_tp = 3
        num_sl = 2
    else:
        # 4+ Parameter: 4×4×4×4 Entry × 2 TP × 2 SL = 1024
        entry_per_param = 4
        num_tp = 2
        num_sl = 2
    
    return entry_per_param, num_tp, num_sl

def generate_parameter_values(param_name: str, param_config: dict, num_values: int) -> list:
    """Generiere optimale Werte für Parameter"""
    
    if param_config.get('values'):
        values = param_config['values']
        if len(values) > num_values:
            step = len(values) // num_values
            return values[::step][:num_values]
        return values
    
    min_val = param_config['min']
    max_val = param_config['max']
    
    if max_val - min_val < num_values:
        return list(range(min_val, max_val + 1))
    
    step = (max_val - min_val) // (num_values - 1)
    values = []
    for i in range(num_values):
        val = min_val + (i * step)
        if val <= max_val:
            values.append(val)
    
    if max_val not in values:
        values[-1] = max_val
    
    return sorted(set(values))

def generate_tp_sl_values(num_tp: int, num_sl: int) -> tuple:
    """Generiere TP/SL Werte"""
    
    tp_base = [30, 40, 50, 60, 75, 90, 110, 130, 150, 180, 220, 270]
    sl_base = [20, 25, 30, 35, 40, 50, 60, 75, 90, 110, 135]
    
    step_tp = len(tp_base) // num_tp
    step_sl = len(sl_base) // num_sl
    
    tp_values = [tp_base[i * step_tp] for i in range(num_tp)]
    sl_values = [sl_base[i * step_sl] for i in range(num_sl)]
    
    return tp_values, sl_values

# MAIN
print("="*80)
print("FINALE CONFIG GENERATION - KORREKT")
print("="*80)

indicator_files = sorted(INDICATORS_PATH.glob("*.py"))
configs_created = 0
stats = defaultdict(int)

for ind_file in indicator_files:
    try:
        ind_num = int(ind_file.stem.split('_')[0])
        ind_name = ind_file.stem
        
        with open(ind_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Extrahiere Parameter
        params = extract_parameters_from_code(code)
        
        # Berechne optimale Verteilung
        entry_per_param, num_tp, num_sl = calculate_optimal_distribution(params, target_total=500)
        
        # Generiere Entry-Parameter
        entry_parameters = {}
        for param_name, param_config in params.items():
            values = generate_parameter_values(param_name, param_config, entry_per_param)
            entry_parameters[param_name] = {
                "values": values,
                "range": {
                    "start": param_config['min'],
                    "end": param_config['max'],
                    "step": (param_config['max'] - param_config['min']) // (len(values) - 1) if len(values) > 1 else 1
                },
                "optimal": values[:min(3, len(values))],
                "description": f"Optimized {param_name} for indicator #{ind_num}"
            }
        
        # Generiere TP/SL
        tp_values, sl_values = generate_tp_sl_values(num_tp, num_sl)
        
        # Berechne tatsächliche Kombinationen
        entry_combos = 1
        for param_config in entry_parameters.values():
            entry_combos *= len(param_config['values'])
        
        total_combos = entry_combos * len(tp_values) * len(sl_values)
        
        # Erstelle Config
        config = {
            "indicator_num": ind_num,
            "indicator_name": ind_name,
            "parameters_detected": list(params.keys()),
            "entry_parameters": entry_parameters,
            "exit_parameters": {
                "tp_pips": {
                    "values": tp_values,
                    "optimal": tp_values[:min(2, len(tp_values))],
                    "description": f"TP for indicator #{ind_num}"
                },
                "sl_pips": {
                    "values": sl_values,
                    "optimal": sl_values[:min(2, len(sl_values))],
                    "description": f"SL for indicator #{ind_num}"
                }
            },
            "combinations_breakdown": {
                "entry_combinations": entry_combos,
                "tp_values": len(tp_values),
                "sl_values": len(sl_values),
                "total_combinations": total_combos
            },
            "max_combinations_per_symbol": 500,
            "priority": "high"
        }
        
        # Speichere
        existing = list(CONFIGS_PATH.glob(f"*_{ind_num:03d}_{ind_name}_config.json"))
        if existing:
            config_file = existing[0]
        else:
            config_file = CONFIGS_PATH / f"{ind_num:03d}_{ind_num:03d}_{ind_name}_config.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        configs_created += 1
        stats[f"{len(params)}_params"] += 1
        stats['total_combos'] += total_combos
        
        if configs_created % 50 == 0:
            print(f"  Erstellt: {configs_created}/467")
        
    except Exception as e:
        print(f"❌ Ind#{ind_num}: {str(e)[:80]}")

avg_combos = stats['total_combos'] / configs_created if configs_created > 0 else 0

print(f"\n✅ Configs erstellt: {configs_created}/467")
print(f"📊 Durchschnittliche Kombinationen: {avg_combos:.0f}")
print(f"\n📈 Parameter-Verteilung:")
for key, count in sorted(stats.items()):
    if '_params' in key:
        print(f"  {key}: {count} Indikatoren")

print(f"\n{'='*80}")
print("KORREKTE CONFIGS ERSTELLT!")
print(f"{'='*80}")
