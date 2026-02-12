"""
Erstelle FINALE Configs für ALLE 467 Indikatoren
Ziel: ~500 Kombinationen pro Indikator durch intelligente Entry × TP × SL Verteilung
"""
import json
import re
from pathlib import Path
from collections import defaultdict

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")
ANALYSIS_FILE = Path("DEEP_PARAMETER_ANALYSIS_SAMPLE.json")

# Lade existierende Analyse
with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
    analysis_data = json.load(f)

def adjust_to_target(entry_combos: int, target: int = 500) -> tuple:
    """
    Berechne TP/SL Anzahl um auf ~target Kombinationen zu kommen
    entry_combos × num_tp × num_sl ≈ target
    """
    if entry_combos >= target:
        # Zu viele Entry-Kombinationen, minimale TP/SL
        return 2, 2
    
    # Berechne benötigte TP×SL
    needed_tpsl = target / entry_combos
    
    # Verteile auf TP und SL (bevorzuge mehr TP als SL)
    if needed_tpsl <= 4:
        return 2, 2
    elif needed_tpsl <= 9:
        return 3, 3
    elif needed_tpsl <= 16:
        return 4, 4
    elif needed_tpsl <= 25:
        return 5, 5
    elif needed_tpsl <= 36:
        return 6, 6
    elif needed_tpsl <= 49:
        return 7, 7
    else:
        return 8, 8

def generate_tp_sl_values(num_tp: int, num_sl: int) -> tuple:
    """Generiere TP/SL Werte"""
    tp_base = [25, 30, 35, 40, 50, 60, 75, 90, 110, 130, 150, 180, 220, 270]
    sl_base = [15, 20, 25, 30, 35, 40, 50, 60, 75, 90, 110, 135]
    
    if num_tp >= len(tp_base):
        tp_values = tp_base
    else:
        step = len(tp_base) // num_tp
        tp_values = [tp_base[i * step] for i in range(num_tp)]
    
    if num_sl >= len(sl_base):
        sl_values = sl_base
    else:
        step = len(sl_base) // num_sl
        sl_values = [sl_base[i * step] for i in range(num_sl)]
    
    return tp_values, sl_values

# MAIN
print("="*80)
print("FINALE CONFIG GENERATION - ALLE 467 INDIKATOREN")
print("="*80)

configs_created = 0
stats = {
    'total_combos': [],
    'param_distribution': defaultdict(int),
    'below_400': 0,
    'between_400_600': 0,
    'above_600': 0
}

for ind_num_str, ind_data in analysis_data.items():
    try:
        ind_num = int(ind_num_str)
        ind_name = ind_data['name']
        params = ind_data['parameters']
        entry_combos = ind_data['total_combinations']
        
        # Berechne optimale TP/SL Anzahl
        num_tp, num_sl = adjust_to_target(entry_combos, target=500)
        
        # Generiere TP/SL
        tp_values, sl_values = generate_tp_sl_values(num_tp, num_sl)
        
        # Berechne finale Kombinationen
        total_combos = entry_combos * len(tp_values) * len(sl_values)
        
        # Erstelle Entry-Parameters aus Analyse
        entry_parameters = {}
        for param_name, param_config in params.items():
            entry_parameters[param_name] = {
                "values": param_config['values'],
                "range": param_config['range'],
                "optimal": param_config['values'][:min(3, len(param_config['values']))],
                "description": f"Optimized {param_name} for indicator #{ind_num}"
            }
        
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
        
        # Stats
        configs_created += 1
        stats['total_combos'].append(total_combos)
        stats['param_distribution'][len(params)] += 1
        
        if total_combos < 400:
            stats['below_400'] += 1
        elif total_combos <= 600:
            stats['between_400_600'] += 1
        else:
            stats['above_600'] += 1
        
        if configs_created % 50 == 0:
            print(f"  Erstellt: {configs_created}/385")
        
    except Exception as e:
        print(f"❌ Ind#{ind_num}: {str(e)[:80]}")

avg_combos = sum(stats['total_combos']) / len(stats['total_combos']) if stats['total_combos'] else 0
min_combos = min(stats['total_combos']) if stats['total_combos'] else 0
max_combos = max(stats['total_combos']) if stats['total_combos'] else 0

print(f"\n✅ Configs erstellt: {configs_created}/385")
print(f"\n📊 KOMBINATIONEN STATISTIK:")
print(f"  Durchschnitt: {avg_combos:.0f}")
print(f"  Minimum: {min_combos}")
print(f"  Maximum: {max_combos}")
print(f"\n  < 400: {stats['below_400']} Indikatoren")
print(f"  400-600: {stats['between_400_600']} Indikatoren")
print(f"  > 600: {stats['above_600']} Indikatoren")

print(f"\n📈 Parameter-Verteilung:")
for num_params, count in sorted(stats['param_distribution'].items()):
    print(f"  {num_params} Parameter: {count} Indikatoren")

print(f"\n{'='*80}")
print("FINALE CONFIGS FÜR ANALYSIERTE INDIKATOREN ERSTELLT!")
print(f"{'='*80}")
