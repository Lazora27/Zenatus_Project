"""Prüfe Status aller 5 laufenden Backtests"""
import re
from pathlib import Path

base = Path(r"/opt/Zenatus_Dokumentation\LOG")

# Log Files
logs = {
    'ERROR_106': base / 'quicktest_error_106_1h_20260130_185432.log',
    'TIMEOUT_9': base / 'quicktest_timeout_9_1h_20260130_185445.log',
    'FEW_8': base / 'quicktest_few_8_1h_20260130_185447.log',
    'FAILED_1': base / 'quicktest_failed_1_1h_20260130_185459.log',
    'UNTESTED_39': base / 'production_untested_39_1h_20260130_185453.log'
}

print("="*80)
print("STATUS UPDATE - ALLE 5 BACKTESTS")
print("="*80)
print()

for name, log_file in logs.items():
    if not log_file.exists():
        print(f"{name}: LOG NICHT GEFUNDEN")
        continue
    
    log_text = log_file.read_text(encoding='utf-8')
    
    # Count results
    success = len(re.findall(r'\[SUCCESS\] Ind#\d+', log_text))
    error = len(re.findall(r'\[ERROR\] Ind#\d+', log_text))
    timeout = len(re.findall(r'TIMEOUT_SIGNALS', log_text))
    few = len(re.findall(r'FEW_SIGNALS', log_text))
    
    # Get last line
    lines = [l for l in log_text.split('\n') if l.strip()]
    last_line = lines[-1] if lines else "Keine Zeilen"
    
    # Check if completed
    completed = "abgeschlossen" in log_text.lower() or "final" in log_text.lower()
    
    print(f"{name}:")
    print(f"  SUCCESS: {success}")
    print(f"  ERROR: {error}")
    print(f"  TIMEOUT: {timeout}")
    print(f"  FEW: {few}")
    print(f"  Status: {'FERTIG' if completed else 'LÄUFT'}")
    print(f"  Letzte Zeile: {last_line[:100]}")
    print()

print("="*80)
