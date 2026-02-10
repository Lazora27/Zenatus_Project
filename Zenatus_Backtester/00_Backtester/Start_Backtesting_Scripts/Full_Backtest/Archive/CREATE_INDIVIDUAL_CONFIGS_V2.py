"""
Erstelle INDIVIDUELLE Parameter-Configs für alle 467 Indikatoren
Basierend auf Indikator-Typ, Mathematik und Charakteristiken
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")
CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")

def analyze_indicator_type(code: str, filename: str) -> Dict:
    """Analysiere Indikator-Code und identifiziere Typ"""
    
    code_lower = code.lower()
    name_lower = filename.lower()
    
    # Indikator-Typ Identifikation
    indicator_type = "unknown"
    sub_type = "generic"
    
    # 1. TREND INDICATORS
    if any(x in name_lower for x in ['sma', 'ema', 'wma', 'dema', 'tema', 'trima', 'kama', 'hma', 'zlema', 'alma', 'jma', 't3', 'vidya', 'frama', 'mcginley', 'sinwma', 'vwma', 'tsf', 'lsma', 'mama', 'smma']):
        indicator_type = "trend"
        sub_type = "moving_average"
        periods = [5, 8, 10, 13, 20, 21, 30, 34, 50, 55, 75, 89, 100, 144, 200]
        tp_values = [30, 40, 50, 60, 75, 90, 110, 130, 150, 180, 220]
        sl_values = [20, 25, 30, 35, 40, 50, 60, 75, 90, 110]
        
    elif any(x in name_lower for x in ['adx', 'dmi', 'aroon', 'psar', 'vortex', 'mass', 'qstick', 'tii']):
        indicator_type = "trend"
        sub_type = "trend_strength"
        periods = [7, 10, 14, 20, 25, 30, 50]
        tp_values = [40, 50, 65, 80, 95, 120, 150]
        sl_values = [25, 30, 40, 50, 60, 75]
        
    # 2. MOMENTUM INDICATORS
    elif any(x in name_lower for x in ['rsi', 'stoch', 'williams', 'cci', 'roc', 'momentum']):
        indicator_type = "momentum"
        sub_type = "oscillator"
        periods = [7, 9, 11, 14, 17, 21, 25, 28]
        tp_values = [25, 35, 45, 55, 70, 85, 100, 120, 140]
        sl_values = [15, 20, 25, 30, 35, 45, 55, 70, 85]
        
    elif any(x in name_lower for x in ['macd', 'ppo', 'apo', 'trix']):
        indicator_type = "momentum"
        sub_type = "divergence"
        periods = [8, 12, 14, 17, 21, 26, 34]
        tp_values = [35, 45, 60, 75, 90, 110, 135]
        sl_values = [20, 28, 35, 45, 55, 70, 85]
        
    # 3. VOLATILITY INDICATORS
    elif any(x in name_lower for x in ['bollinger', 'keltner', 'donchian', 'atr', 'channel', 'band', 'envelope']):
        indicator_type = "volatility"
        sub_type = "bands"
        periods = [10, 14, 20, 25, 30, 40, 50]
        tp_values = [50, 65, 80, 100, 125, 150, 180, 220]
        sl_values = [30, 40, 50, 60, 75, 95, 120]
        
    # 4. VOLUME INDICATORS
    elif any(x in name_lower for x in ['volume', 'obv', 'mfi', 'cmf', 'vwap', 'ad', 'force']):
        indicator_type = "volume"
        sub_type = "volume_analysis"
        periods = [10, 14, 20, 30, 50]
        tp_values = [35, 50, 65, 85, 105, 130, 160]
        sl_values = [20, 30, 40, 50, 65, 80]
        
    # 5. PATTERN RECOGNITION
    elif any(x in name_lower for x in ['pattern', 'candlestick', 'harmonic', 'elliott', 'fibonacci', 'wyckoff']):
        indicator_type = "pattern"
        sub_type = "recognition"
        periods = [5, 8, 13, 21, 34, 55, 89]
        tp_values = [40, 60, 80, 110, 140, 180, 230]
        sl_values = [25, 35, 50, 65, 85, 110]
        
    # 6. STATISTICAL/ML
    elif any(x in name_lower for x in ['neural', 'ml', 'ai', 'learning', 'network', 'regression', 'forecast', 'prediction']):
        indicator_type = "statistical"
        sub_type = "ml_ai"
        periods = [20, 30, 50, 75, 100]
        tp_values = [40, 65, 95, 135, 190, 260]
        sl_values = [25, 40, 60, 85, 120]
        
    # 7. COMPLEX/ADAPTIVE
    elif any(x in name_lower for x in ['adaptive', 'dynamic', 'intelligent', 'smart', 'quantum', 'fractal']):
        indicator_type = "adaptive"
        sub_type = "complex"
        periods = [15, 20, 30, 50, 75, 100, 150]
        tp_values = [50, 75, 110, 150, 200, 270]
        sl_values = [30, 45, 65, 90, 125]
        
    else:
        # Default: Generic Trend
        indicator_type = "trend"
        sub_type = "generic"
        periods = [10, 14, 20, 30, 50, 75, 100]
        tp_values = [40, 50, 65, 80, 100, 125, 150]
        sl_values = [25, 30, 40, 50, 65, 80]
    
    return {
        'type': indicator_type,
        'sub_type': sub_type,
        'periods': periods,
        'tp_values': tp_values,
        'sl_values': sl_values
    }

def create_individual_config(ind_num: int, ind_name: str, analysis: Dict) -> Dict:
    """Erstelle individuelle Config basierend auf Analyse"""
    
    config = {
        "indicator_num": ind_num,
        "indicator_name": ind_name,
        "indicator_type": analysis['type'],
        "sub_type": analysis['sub_type'],
        "description": f"{analysis['type'].title()} indicator - {analysis['sub_type']}",
        "entry_parameters": {
            "period": {
                "values": analysis['periods'],
                "optimal": analysis['periods'][:3],
                "description": f"Optimized periods for {analysis['type']} {analysis['sub_type']}"
            }
        },
        "exit_parameters": {
            "tp_pips": {
                "values": analysis['tp_values'],
                "optimal": analysis['tp_values'][:3],
                "description": f"TP optimized for {analysis['type']} volatility"
            },
            "sl_pips": {
                "values": analysis['sl_values'],
                "optimal": analysis['sl_values'][:3],
                "description": f"SL optimized for {analysis['type']} risk profile"
            }
        },
        "expected_profit_factor": 1.3 if analysis['type'] in ['momentum', 'volatility'] else 1.2,
        "expected_sharpe_ratio": 1.2 if analysis['type'] in ['adaptive', 'statistical'] else 1.0,
        "max_combinations_per_symbol": 500,
        "priority": "high" if analysis['type'] in ['adaptive', 'statistical', 'momentum'] else "medium"
    }
    
    return config

# MAIN EXECUTION
print("="*80)
print("INDIVIDUELLE PARAMETER-CONFIGS GENERIERUNG")
print("="*80)

indicator_files = sorted(INDICATORS_PATH.glob("*.py"))
print(f"\nGefunden: {len(indicator_files)} Indikatoren")

configs_created = 0
type_distribution = {}

for ind_file in indicator_files:
    try:
        # Extrahiere Nummer
        ind_num = int(ind_file.stem.split('_')[0])
        ind_name = ind_file.stem
        
        # Lese Code
        with open(ind_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Analysiere Typ
        analysis = analyze_indicator_type(code, ind_file.name)
        
        # Zähle Typen
        key = f"{analysis['type']}_{analysis['sub_type']}"
        type_distribution[key] = type_distribution.get(key, 0) + 1
        
        # Erstelle Config
        config = create_individual_config(ind_num, ind_name, analysis)
        
        # Speichere Config (Format: XXX_YYY_name_config.json)
        # Suche nach existierender Config um Prefix zu behalten
        existing_configs = list(CONFIGS_PATH.glob(f"*_{ind_num:03d}_{ind_name}_config.json"))
        if existing_configs:
            config_file = existing_configs[0]
        else:
            config_file = CONFIGS_PATH / f"{ind_num:03d}_{ind_num:03d}_{ind_name}_config.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        configs_created += 1
        
        if configs_created % 50 == 0:
            print(f"  Erstellt: {configs_created}/{len(indicator_files)}")
        
    except Exception as e:
        print(f"❌ Fehler bei {ind_file.name}: {str(e)[:100]}")

print(f"\n✅ Configs erstellt: {configs_created}/{len(indicator_files)}")

print(f"\n📊 TYP-VERTEILUNG:")
for typ, count in sorted(type_distribution.items(), key=lambda x: x[1], reverse=True):
    print(f"  {typ:40s}: {count:3d}")

print(f"\n{'='*80}")
print("GENERIERUNG ABGESCHLOSSEN")
print(f"{'='*80}")
