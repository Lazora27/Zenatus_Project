"""Prüfe PRODUCTION_SUCCESS_92 Status"""
from pathlib import Path
import re

log_file = Path(r"/opt/Zenatus_Dokumentation\LOG\production_success_92_1h_20260130_123328.log")

if not log_file.exists():
    print("Log file not found!")
    exit(1)

log_text = log_file.read_text(encoding='utf-8')

# Count results
success = len(re.findall(r'\[SUCCESS\] Ind#\d+', log_text))
error = len(re.findall(r'\[ERROR\] Ind#\d+', log_text))
timeout = len(re.findall(r'TIMEOUT_SIGNALS', log_text))
few = len(re.findall(r'FEW_SIGNALS', log_text))

# Extract last line
lines = [l for l in log_text.split('\n') if l.strip()]
last_line = lines[-1] if lines else "No lines"

# Check if completed
completed = "Backtest abgeschlossen" in log_text or "FINAL RESULTS" in log_text

print(f"PRODUCTION_SUCCESS_92 STATUS:")
print(f"SUCCESS: {success}")
print(f"ERROR: {error}")
print(f"TIMEOUT: {timeout}")
print(f"FEW_SIGNALS: {few}")
print(f"TOTAL: {success + error + timeout + few}")
print(f"COMPLETED: {completed}")
print(f"\nLAST LINE: {last_line}")
