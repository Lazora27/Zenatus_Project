"""
Analysiere Parameter-Configs: Sind sie individuell oder generisch?
"""
import json
from pathlib import Path
from collections import defaultdict

CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")
INDICATORS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")

print("="*80)
print("PARAMETER-CONFIG ANALYSE")
print("="*80)

# 1. Zähle Configs
config_files = list(CONFIGS_PATH.glob("*_config.json"))
indicator_files = list(INDICATORS_PATH.glob("*.py"))

print(f"\n📊 STATISTIK:")
print(f"Indicator-Files: {len(indicator_files)}")
print(f"Config-Files: {len(config_files)}")
print(f"Coverage: {len(config_files)/len(indicator_files)*100:.1f}%")

# 2. Analysiere Config-Inhalte
period_patterns = defaultdict(list)
tp_sl_patterns = defaultdict(list)

print(f"\n🔍 ANALYSIERE CONFIGS...")
for config_file in config_files[:50]:  # Sample erste 50
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Extrahiere Patterns
        entry_params = config.get('entry_parameters', {})
        exit_params = config.get('exit_parameters', {})
        
        period_values = tuple(entry_params.get('period', {}).get('values', []))
        tp_values = tuple(exit_params.get('tp_pips', {}).get('values', []))
        sl_values = tuple(exit_params.get('sl_pips', {}).get('values', []))
        
        period_patterns[period_values].append(config_file.stem)
        tp_sl_patterns[(tp_values, sl_values)].append(config_file.stem)
        
    except Exception as e:
        print(f"❌ Fehler bei {config_file.name}: {str(e)[:50]}")

# 3. Zeige Duplikate
print(f"\n📋 PERIOD-PATTERNS (Top 10):")
sorted_periods = sorted(period_patterns.items(), key=lambda x: len(x[1]), reverse=True)
for i, (pattern, configs) in enumerate(sorted_periods[:10], 1):
    print(f"{i}. {len(configs):3d} Configs mit Pattern: {pattern[:5]}...")
    if len(configs) <= 3:
        for cfg in configs:
            print(f"   - {cfg}")

print(f"\n📋 TP/SL-PATTERNS (Top 10):")
sorted_tpsl = sorted(tp_sl_patterns.items(), key=lambda x: len(x[1]), reverse=True)
for i, (pattern, configs) in enumerate(sorted_tpsl[:10], 1):
    tp_pattern, sl_pattern = pattern
    print(f"{i}. {len(configs):3d} Configs mit TP={len(tp_pattern)} SL={len(sl_pattern)}")
    if len(configs) <= 3:
        for cfg in configs:
            print(f"   - {cfg}")

# 4. Identifiziere fehlende Configs
print(f"\n❌ FEHLENDE CONFIGS:")
indicator_nums = set()
for ind_file in indicator_files:
    try:
        num = int(ind_file.stem.split('_')[0])
        indicator_nums.add(num)
    except:
        pass

config_nums = set()
for cfg_file in config_files:
    try:
        # Format: XXX_YYY_name_config.json
        parts = cfg_file.stem.split('_')
        if len(parts) >= 2:
            num = int(parts[1])  # Zweite Nummer
            config_nums.add(num)
    except:
        pass

missing = sorted(indicator_nums - config_nums)
print(f"Fehlende Configs: {len(missing)}")
if len(missing) <= 20:
    print(f"Nummern: {missing}")
else:
    print(f"Erste 20: {missing[:20]}")
    print(f"Letzte 20: {missing[-20:]}")

# 5. Prüfe Individualität
print(f"\n🎯 INDIVIDUALITÄTS-SCORE:")
unique_period_patterns = len(period_patterns)
unique_tpsl_patterns = len(tp_sl_patterns)
total_configs = len(config_files)

individuality_score = (unique_period_patterns / total_configs * 100) if total_configs > 0 else 0
print(f"Unique Period-Patterns: {unique_period_patterns}/{total_configs} ({individuality_score:.1f}%)")
print(f"Unique TP/SL-Patterns: {unique_tpsl_patterns}/{total_configs}")

if individuality_score < 50:
    print("\n⚠️  WARNUNG: Configs sind zu generisch! (<50% unique)")
elif individuality_score < 80:
    print("\n⚠️  Configs sind teilweise generisch (50-80% unique)")
else:
    print("\n✅ Configs sind individuell! (>80% unique)")

print(f"\n{'='*80}")
print("ANALYSE ABGESCHLOSSEN")
print(f"{'='*80}")
