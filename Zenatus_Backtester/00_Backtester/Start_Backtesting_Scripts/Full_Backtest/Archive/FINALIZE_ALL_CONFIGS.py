"""
Finalisiere ALLE 467 Configs:
1. Fehlende Indikatoren mit Default-Config
2. Limitiere über 600 Kombinationen auf ~500
"""
import json
from pathlib import Path

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")

# Finde alle Indikatoren
all_indicator_files = sorted(INDICATORS_PATH.glob("*.py"))
all_indicator_nums = set()
for ind_file in all_indicator_files:
    try:
        ind_num = int(ind_file.stem.split('_')[0])
        all_indicator_nums.add(ind_num)
    except:
        pass

# Finde existierende Configs
existing_configs = set()
for config_file in CONFIGS_PATH.glob("*_config.json"):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        ind_num = config.get('indicator_num')
        if ind_num:
            existing_configs.add(ind_num)
    except:
        pass

missing = sorted(all_indicator_nums - existing_configs)

print("="*80)
print("FINALISIERE ALLE CONFIGS")
print("="*80)
print(f"\nTotal Indikatoren: {len(all_indicator_nums)}")
print(f"Existierende Configs: {len(existing_configs)}")
print(f"Fehlende Configs: {len(missing)}")

# Erstelle Default-Configs für fehlende
created = 0
for ind_num in missing:
    # Finde Indikator-File
    ind_files = list(INDICATORS_PATH.glob(f"{ind_num:03d}_*.py"))
    if not ind_files:
        continue
    
    ind_file = ind_files[0]
    ind_name = ind_file.stem
    
    # Default Config: 20 period × 5 TP × 5 SL = 500
    config = {
        "indicator_num": ind_num,
        "indicator_name": ind_name,
        "parameters_detected": ["period"],
        "entry_parameters": {
            "period": {
                "values": [5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125, 135, 145, 155, 165, 175, 185, 200],
                "range": {"start": 5, "end": 200, "step": 10},
                "optimal": [5, 15, 25],
                "description": f"Default period for indicator #{ind_num}"
            }
        },
        "exit_parameters": {
            "tp_pips": {
                "values": [30, 50, 75, 110, 150],
                "optimal": [30, 50],
                "description": f"TP for indicator #{ind_num}"
            },
            "sl_pips": {
                "values": [20, 30, 40, 60, 90],
                "optimal": [20, 30],
                "description": f"SL for indicator #{ind_num}"
            }
        },
        "combinations_breakdown": {
            "entry_combinations": 20,
            "tp_values": 5,
            "sl_values": 5,
            "total_combinations": 500
        },
        "max_combinations_per_symbol": 500,
        "priority": "medium"
    }
    
    config_file = CONFIGS_PATH / f"{ind_num:03d}_{ind_num:03d}_{ind_name}_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    created += 1

print(f"\n✅ Default-Configs erstellt: {created}")

# Limitiere Configs mit >600 Kombinationen
limited = 0
for config_file in CONFIGS_PATH.glob("*_config.json"):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        breakdown = config.get('combinations_breakdown', {})
        total_combos = breakdown.get('total_combinations', 0)
        
        if total_combos > 600:
            # Reduziere Entry-Parameter
            entry_params = config.get('entry_parameters', {})
            reduction_needed = 600 / total_combos
            
            for param_name, param_config in entry_params.items():
                values = param_config['values']
                new_count = max(3, int(len(values) * reduction_needed))
                param_config['values'] = values[:new_count]
                param_config['optimal'] = values[:min(3, new_count)]
            
            # Neuberechnung
            entry_combos = 1
            for param_config in entry_params.values():
                entry_combos *= len(param_config['values'])
            
            tp_count = len(config['exit_parameters']['tp_pips']['values'])
            sl_count = len(config['exit_parameters']['sl_pips']['values'])
            new_total = entry_combos * tp_count * sl_count
            
            config['combinations_breakdown']['entry_combinations'] = entry_combos
            config['combinations_breakdown']['total_combinations'] = new_total
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            limited += 1
    except Exception as e:
        pass

print(f"✅ Configs limitiert (<600): {limited}")

# Finale Statistik
all_combos = []
for config_file in CONFIGS_PATH.glob("*_config.json"):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        total = config.get('combinations_breakdown', {}).get('total_combinations', 0)
        if total > 0:
            all_combos.append(total)
    except:
        pass

if all_combos:
    avg = sum(all_combos) / len(all_combos)
    print(f"\n📊 FINALE STATISTIK:")
    print(f"  Total Configs: {len(all_combos)}")
    print(f"  Durchschnitt: {avg:.0f} Kombinationen")
    print(f"  Min: {min(all_combos)}")
    print(f"  Max: {max(all_combos)}")

print(f"\n{'='*80}")
print("ALLE CONFIGS FINALISIERT!")
print(f"{'='*80}")
