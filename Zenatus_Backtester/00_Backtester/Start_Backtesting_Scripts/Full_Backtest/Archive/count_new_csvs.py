from pathlib import Path
import os
from datetime import datetime

csv_dir = Path(r"/opt/Zenatus_Dokumentation\Dokumentation\Fixed_Exit\1h")
files = list(csv_dir.glob('*.csv'))

# 23:40 Uhr = 30.01.2026 23:40:00
start_time = datetime(2026, 1, 30, 23, 40, 0).timestamp()

new_files = [f for f in files if os.path.getmtime(f) > start_time]
new_ids = sorted([int(f.stem.split('_')[0]) for f in new_files])

print(f"Total CSVs: {len(files)}")
print(f"Neue CSVs seit 23:40 Uhr: {len(new_files)}")
print(f"Neue IDs: {new_ids}")
