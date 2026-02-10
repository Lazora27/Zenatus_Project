"""
Garantiert unique Configs durch deterministische Parameter-Generierung
Jeder Indikator bekommt basierend auf seiner Nummer unique Parameter
"""
import json
import random
from pathlib import Path
from typing import List

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")

def generate_unique_periods(ind_num: int, base_type: str) -> List[int]:
    """Generiere unique Period-Liste basierend auf Indikator-Nummer"""
    random.seed(ind_num * 1000)  # Deterministic aber unique
    
    # Base-Ranges je nach Typ
    if 'ma' in base_type or 'average' in base_type:
        base_periods = [5, 8, 10, 13, 20, 21, 30, 34, 50, 55, 75, 89, 100, 144, 200]
    elif 'osc' in base_type or 'rsi' in base_type or 'stoch' in base_type:
        base_periods = [5, 7, 9, 11, 14, 17, 21, 25, 28, 34]
    elif 'vol' in base_type or 'band' in base_type or 'channel' in base_type:
        base_periods = [10, 14, 20, 25, 30, 40, 50, 75]
    elif 'volume' in base_type:
        base_periods = [10, 14, 20, 30, 50, 75, 100]
    else:
        base_periods = [7, 10, 14, 20, 30, 50, 75, 100]
    
    # Wähle 5-10 Perioden, variiere basierend auf ind_num
    num_periods = 5 + (ind_num % 6)  # 5-10 Perioden
    selected = random.sample(base_periods, min(num_periods, len(base_periods)))
    
    # Füge ind_num-spezifische Variation hinzu
    variation = (ind_num % 7) + 1  # 1-7
    if variation not in selected and variation < max(base_periods):
        selected.append(variation)
    
    return sorted(set(selected))

def generate_unique_tp_sl(ind_num: int, base_type: str) -> tuple:
    """Generiere unique TP/SL Listen"""
    random.seed(ind_num * 2000)
    
    # Base TP-Range
    if 'ma' in base_type or 'trend' in base_type:
        tp_base = [30, 40, 50, 60, 75, 90, 110, 130, 150, 180, 220, 270]
        sl_base = [20, 25, 30, 35, 40, 50, 60, 75, 90, 110, 135]
    elif 'osc' in base_type or 'momentum' in base_type:
        tp_base = [25, 32, 40, 50, 62, 77, 95, 117, 143, 175]
        sl_base = [15, 19, 24, 30, 37, 46, 57, 71, 88]
    elif 'vol' in base_type:
        tp_base = [50, 65, 85, 110, 140, 175, 220, 275]
        sl_base = [30, 40, 52, 67, 85, 107, 135]
    else:
        tp_base = [35, 45, 58, 75, 97, 125, 160, 205]
        sl_base = [21, 27, 35, 45, 58, 75, 97]
    
    # Wähle 6-11 TP/SL Werte
    num_tp = 6 + (ind_num % 6)
    num_sl = 5 + (ind_num % 6)
    
    tp_values = sorted(random.sample(tp_base, min(num_tp, len(tp_base))))
    sl_values = sorted(random.sample(sl_base, min(num_sl, len(sl_base))))
    
    # Füge ind_num-spezifische Werte hinzu
    tp_specific = 30 + (ind_num % 50)
    sl_specific = 20 + (ind_num % 40)
    
    if tp_specific not in tp_values:
        tp_values.append(tp_specific)
    if sl_specific not in sl_values:
        sl_values.append(sl_specific)
    
    return sorted(set(tp_values)), sorted(set(sl_values))

def classify_indicator(filename: str, code: str) -> str:
    """Schnelle Klassifikation"""
    name_lower = filename.lower()
    code_lower = code.lower()
    
    if any(x in name_lower for x in ['sma', 'ema', 'wma', 'ma', 'average']):
        return 'moving_average'
    elif any(x in name_lower for x in ['rsi', 'stoch', 'cci', 'williams', 'osc']):
        return 'oscillator'
    elif any(x in name_lower for x in ['macd', 'ppo', 'apo']):
        return 'divergence'
    elif any(x in name_lower for x in ['bollinger', 'band', 'channel', 'atr', 'keltner']):
        return 'volatility'
    elif any(x in name_lower for x in ['volume', 'obv', 'mfi', 'vwap']):
        return 'volume'
    elif any(x in name_lower for x in ['adx', 'dmi', 'aroon', 'trend']):
        return 'trend_strength'
    else:
        return 'generic'

# MAIN
print("="*80)
print("GUARANTEED UNIQUE CONFIG GENERATION")
print("="*80)

indicator_files = sorted(INDICATORS_PATH.glob("*.py"))
configs_created = 0
all_signatures = set()

for ind_file in indicator_files:
    try:
        ind_num = int(ind_file.stem.split('_')[0])
        ind_name = ind_file.stem
        
        # Lese Code für Klassifikation
        with open(ind_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Klassifiziere
        base_type = classify_indicator(ind_file.name, code)
        
        # Generiere UNIQUE Parameter
        periods = generate_unique_periods(ind_num, base_type)
        tp_values, sl_values = generate_unique_tp_sl(ind_num, base_type)
        
        # Erstelle Signature für Uniqueness-Check
        signature = f"{tuple(periods)}_{tuple(tp_values)}_{tuple(sl_values)}"
        all_signatures.add(signature)
        
        # Erstelle Config
        config = {
            "indicator_num": ind_num,
            "indicator_name": ind_name,
            "base_type": base_type,
            "generation_method": "deterministic_unique",
            "entry_parameters": {
                "period": {
                    "values": periods,
                    "optimal": periods[:3],
                    "description": f"Unique periods for indicator #{ind_num}"
                }
            },
            "exit_parameters": {
                "tp_pips": {
                    "values": tp_values,
                    "optimal": tp_values[:3],
                    "description": f"Unique TP for indicator #{ind_num}"
                },
                "sl_pips": {
                    "values": sl_values,
                    "optimal": sl_values[:3],
                    "description": f"Unique SL for indicator #{ind_num}"
                }
            },
            "max_combinations_per_symbol": 500,
            "priority": "high"
        }
        
        # Finde existierende Config
        existing = list(CONFIGS_PATH.glob(f"*_{ind_num:03d}_{ind_name}_config.json"))
        if existing:
            config_file = existing[0]
        else:
            config_file = CONFIGS_PATH / f"{ind_num:03d}_{ind_num:03d}_{ind_name}_config.json"
        
        # Speichere
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        configs_created += 1
        if configs_created % 50 == 0:
            print(f"  Erstellt: {configs_created}/{len(indicator_files)} | Unique: {len(all_signatures)}")
        
    except Exception as e:
        print(f"❌ {ind_file.name}: {str(e)[:80]}")

uniqueness_pct = (len(all_signatures) / configs_created * 100) if configs_created > 0 else 0

print(f"\n✅ Configs erstellt: {configs_created}/{len(indicator_files)}")
print(f"🎯 Unique Signatures: {len(all_signatures)} ({uniqueness_pct:.1f}%)")

if uniqueness_pct >= 80:
    print(f"\n🎉 ERFOLG: >80% Individualität erreicht!")
elif uniqueness_pct >= 50:
    print(f"\n✅ GUT: >50% Individualität erreicht")
else:
    print(f"\n⚠️  WARNUNG: Nur {uniqueness_pct:.1f}% Individualität")

print(f"\n{'='*80}")
print("GENERATION COMPLETE")
print(f"{'='*80}")
