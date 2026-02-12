import re
from collections import Counter
from pathlib import Path

LOG_FILE = Path(r"/opt/Zenatus_Dokumentation\LOG\problem_fix_1h_20260131_035953.log")

logs = open(LOG_FILE, 'r', encoding='utf-8').read()

# Extrahiere alle Timeout-Indikatoren
timeouts = re.findall(r'Ind#(\d+).*VectorBT TIMEOUT', logs)
timeout_counts = Counter(timeouts)

print("="*80)
print("TIMEOUT-ANALYSE")
print("="*80)
print(f"Total Timeouts: {len(timeouts)}")
print(f"Unique Indikatoren: {len(timeout_counts)}")
print()
print("Top 30 Timeout-Indikatoren:")
print("-"*80)

timeout_list = []
for ind, count in timeout_counts.most_common(30):
    ind_num = int(ind)
    print(f"Ind#{ind_num:03d}: {count:3d} Timeouts")
    timeout_list.append(ind_num)

print()
print(f"Timeout-Indikatoren IDs: {sorted(timeout_list)}")
print()
print(f"Total unique Timeout-Indikatoren: {len(timeout_list)}")
