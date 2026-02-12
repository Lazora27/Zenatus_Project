"""
Analysiere ALLE Indikatoren: Welche Entry-Parameter brauchen sie wirklich?
"""
import re
import ast
from pathlib import Path
from collections import defaultdict

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")

def extract_parameters_from_code(code: str, filename: str) -> dict:
    """Extrahiere alle Parameter die der Indikator verwendet"""
    
    params_found = {
        'period': False,
        'fast_period': False,
        'slow_period': False,
        'signal_period': False,
        'length': False,
        'window': False,
        'lookback': False,
        'threshold': False,
        'multiplier': False,
        'deviation': False,
        'vfactor': False,
        'alpha': False,
        'beta': False,
        'k_period': False,
        'd_period': False,
        'smooth_k': False,
        'smooth_d': False,
        'atr_period': False,
        'ema_period': False,
        'sma_period': False,
        'other_params': []
    }
    
    code_lower = code.lower()
    
    # Suche nach Parameter-Verwendung in Funktionen
    # Pattern: function(..., period=...) oder function(..., fast_period=...)
    param_patterns = [
        r'\bperiod\s*[=:]',
        r'\bfast_period\s*[=:]',
        r'\bslow_period\s*[=:]',
        r'\bsignal_period\s*[=:]',
        r'\blength\s*[=:]',
        r'\bwindow\s*[=:]',
        r'\blookback\s*[=:]',
        r'\bthreshold\s*[=:]',
        r'\bmultiplier\s*[=:]',
        r'\bdeviation\s*[=:]',
        r'\bvfactor\s*[=:]',
        r'\balpha\s*[=:]',
        r'\bbeta\s*[=:]',
        r'\bk_period\s*[=:]',
        r'\bd_period\s*[=:]',
        r'\bsmooth_k\s*[=:]',
        r'\bsmooth_d\s*[=:]',
        r'\batr_period\s*[=:]',
        r'\bema_period\s*[=:]',
        r'\bsma_period\s*[=:]',
    ]
    
    for pattern in param_patterns:
        if re.search(pattern, code_lower):
            param_name = pattern.replace(r'\b', '').replace(r'\s*[=:]', '')
            if param_name in params_found:
                params_found[param_name] = True
    
    # Suche nach PARAMETERS Dictionary
    if 'PARAMETERS' in code:
        try:
            # Extrahiere PARAMETERS Block
            params_match = re.search(r'PARAMETERS\s*=\s*\{([^}]+)\}', code, re.DOTALL)
            if params_match:
                params_block = params_match.group(1)
                # Finde alle Keys
                for key_match in re.finditer(r"['\"](\w+)['\"]", params_block):
                    key = key_match.group(1).lower()
                    if key in params_found:
                        params_found[key] = True
                    elif key not in ['default', 'min', 'max', 'values', 'step', 'optimize', 'description']:
                        params_found['other_params'].append(key)
        except:
            pass
    
    # Suche nach generate_signals Funktion Signatur
    gen_signals_match = re.search(r'def\s+generate_signals[^(]*\(([^)]+)\)', code)
    if gen_signals_match:
        sig = gen_signals_match.group(1)
        for param in ['period', 'fast_period', 'slow_period', 'signal_period', 'length', 'window', 'threshold']:
            if param in sig.lower():
                params_found[param] = True
    
    return params_found

# MAIN
print("="*80)
print("INDIKATOR PARAMETER ANALYSE")
print("="*80)

indicator_files = sorted(INDICATORS_PATH.glob("*.py"))
param_stats = defaultdict(int)
indicator_params = {}

for ind_file in indicator_files:
    try:
        ind_num = int(ind_file.stem.split('_')[0])
        ind_name = ind_file.stem
        
        with open(ind_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        params = extract_parameters_from_code(code, ind_file.name)
        
        # Zähle verwendete Parameter
        used_params = [k for k, v in params.items() if v and k != 'other_params']
        if params['other_params']:
            used_params.extend(params['other_params'])
        
        indicator_params[ind_num] = {
            'name': ind_name,
            'params': used_params
        }
        
        for param in used_params:
            param_stats[param] += 1
        
    except Exception as e:
        print(f"❌ {ind_file.name}: {str(e)[:60]}")

print(f"\n📊 PARAMETER STATISTIK:")
print(f"Analysierte Indikatoren: {len(indicator_params)}")
print(f"\nHäufigste Parameter:")
for param, count in sorted(param_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
    pct = count / len(indicator_params) * 100
    print(f"  {param:20s}: {count:3d} ({pct:5.1f}%)")

# Finde Indikatoren mit speziellen Parametern
print(f"\n🔍 SPEZIELLE PARAMETER-KOMBINATIONEN:")

# MACD-Typ (fast + slow + signal)
macd_type = [ind for ind, data in indicator_params.items() 
             if 'fast_period' in data['params'] and 'slow_period' in data['params']]
print(f"\nMACD-Typ (fast/slow/signal): {len(macd_type)} Indikatoren")
if len(macd_type) <= 10:
    for ind_num in macd_type:
        print(f"  #{ind_num:03d}: {indicator_params[ind_num]['name']}")

# Stochastic-Typ (k + d)
stoch_type = [ind for ind, data in indicator_params.items() 
              if 'k_period' in data['params'] or 'd_period' in data['params']]
print(f"\nStochastic-Typ (k/d): {len(stoch_type)} Indikatoren")
if len(stoch_type) <= 10:
    for ind_num in stoch_type:
        print(f"  #{ind_num:03d}: {indicator_params[ind_num]['name']}")

# Bollinger-Typ (period + deviation/multiplier)
bollinger_type = [ind for ind, data in indicator_params.items() 
                  if ('period' in data['params'] and 
                      ('deviation' in data['params'] or 'multiplier' in data['params']))]
print(f"\nBollinger-Typ (period + deviation): {len(bollinger_type)} Indikatoren")
if len(bollinger_type) <= 10:
    for ind_num in bollinger_type:
        print(f"  #{ind_num:03d}: {indicator_params[ind_num]['name']}")

# Nur Period
only_period = [ind for ind, data in indicator_params.items() 
               if data['params'] == ['period']]
print(f"\nNur Period: {len(only_period)} Indikatoren")

# Komplexe (>3 Parameter)
complex_params = [ind for ind, data in indicator_params.items() 
                  if len(data['params']) > 3]
print(f"\nKomplex (>3 Parameter): {len(complex_params)} Indikatoren")
if len(complex_params) <= 10:
    for ind_num in complex_params:
        params = indicator_params[ind_num]['params']
        print(f"  #{ind_num:03d}: {indicator_params[ind_num]['name']} - {params}")

print(f"\n{'='*80}")
print("ANALYSE ABGESCHLOSSEN")
print(f"{'='*80}")

# Speichere Ergebnis
import json
output_file = Path("INDICATOR_PARAMETERS_ANALYSIS.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(indicator_params, f, indent=2, ensure_ascii=False)
print(f"\n✅ Gespeichert: {output_file}")
