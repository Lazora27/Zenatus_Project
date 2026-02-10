"""
Entferne alte generische Configs, behalte nur neue individuelle
"""
from pathlib import Path
import re

CONFIGS_PATH = Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Config")

print("="*80)
print("CLEANUP ALTER CONFIGS")
print("="*80)

# Finde alle Config-Files
all_configs = list(CONFIGS_PATH.glob("*_config.json"))
print(f"\nGesamt Configs: {len(all_configs)}")

# Gruppiere nach Indikator-Nummer (zweite Nummer im Namen)
from collections import defaultdict
configs_by_num = defaultdict(list)

for cfg in all_configs:
    # Format: XXX_YYY_name_config.json
    match = re.match(r'(\d+)_(\d+)_(.+)_config\.json', cfg.name)
    if match:
        prefix, ind_num, name = match.groups()
        configs_by_num[int(ind_num)].append((cfg, int(prefix)))

# Für jeden Indikator: Behalte nur die neueste Config (höchster Prefix)
deleted = 0
kept = 0

for ind_num, configs in sorted(configs_by_num.items()):
    if len(configs) > 1:
        # Sortiere nach Prefix (höher = neuer)
        configs_sorted = sorted(configs, key=lambda x: x[1], reverse=True)
        
        # Behalte erste (neueste)
        keep_cfg = configs_sorted[0][0]
        kept += 1
        
        # Lösche Rest
        for cfg, prefix in configs_sorted[1:]:
            cfg.unlink()
            deleted += 1
            print(f"  Gelöscht: {cfg.name}")
    else:
        kept += 1

print(f"\n✅ Behalten: {kept}")
print(f"❌ Gelöscht: {deleted}")

print(f"\n{'='*80}")
print("CLEANUP ABGESCHLOSSEN")
print(f"{'='*80}")
