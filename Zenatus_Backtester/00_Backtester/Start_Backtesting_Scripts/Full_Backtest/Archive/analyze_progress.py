"""Analysiere PROBLEMSOLVING Progress"""
from pathlib import Path
import re
from datetime import datetime

log_file = Path(r"/opt/Zenatus_Dokumentation\LOG\problemsolving_1h_20260130_163303.log")

if not log_file.exists():
    print("Log file not found!")
    exit(1)

log_text = log_file.read_text(encoding='utf-8')

# Count results
success = len(re.findall(r'\[SUCCESS\] Ind#\d+', log_text))
error = len(re.findall(r'\[ERROR\] Ind#\d+', log_text))
timeout_signals = len(re.findall(r'TIMEOUT_SIGNALS', log_text))
few_signals = len(re.findall(r'FEW_SIGNALS', log_text))
warnings = len(re.findall(r'\[WARNING\]', log_text))

# Extract processed indicators
processed_ids = set()
for match in re.finditer(r'Ind#(\d+)', log_text):
    processed_ids.add(int(match.group(1)))

# Calculate time
start_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\].*Backtest System gestartet', log_text)
if start_match:
    start_time = start_match.group(1)
    current_time = datetime.now().strftime('%H:%M:%S')
    
    start_dt = datetime.strptime(start_time, '%H:%M:%S')
    current_dt = datetime.strptime(current_time, '%H:%M:%S')
    
    if current_dt < start_dt:
        current_dt = current_dt.replace(day=current_dt.day + 1)
    
    elapsed = (current_dt - start_dt).total_seconds() / 3600
    
    print(f"START: {start_time}")
    print(f"NOW: {current_time}")
    print(f"ELAPSED: {elapsed:.1f}h")
    print()

print(f"PROCESSED INDICATORS: {len(processed_ids)}")
print(f"SUCCESS: {success}")
print(f"ERROR: {error}")
print(f"TIMEOUT_SIGNALS: {timeout_signals}")
print(f"FEW_SIGNALS: {few_signals}")
print(f"WARNINGS: {warnings}")
print()

# Show which indicators are being processed
print(f"Indicator IDs seen: {sorted(processed_ids)[:20]}...")
print()

# Show last 10 lines
lines = log_text.split('\n')
print("LAST 10 LINES:")
for line in lines[-10:]:
    if line.strip():
        print(line)
