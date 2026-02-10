"""
BACKTEST MONITOR - Zeigt Fortschritt aller laufenden Backtests
"""
import time
from pathlib import Path
from datetime import datetime
import re

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
LOG_PATH = BASE_PATH / "LOGS"

# Relevante Log-Dateien (neueste von jedem Typ)
LOG_PATTERNS = {
    "STABLE_SUCCESS": "stable_success_1h_*.log",
    "DEBUG": "debug_1h_*.log",
    "QUICKTEST_ERROR": "quicktest_error_106_1h_*.log",
    "QUICKTEST_TIMEOUT": "quicktest_timeout_9_1h_*.log",
    "QUICKTEST_FEW": "quicktest_few_8_1h_*.log",
    "QUICKTEST_FAILED": "quicktest_failed_1_1h_*.log",
    "PRODUCTION_UNTESTED": "production_untested_39_1h_*.log"
}

def get_latest_log(pattern):
    """Finde neueste Log-Datei für Pattern"""
    logs = sorted(LOG_PATH.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)
    return logs[0] if logs else None

def parse_log_status(log_file):
    """Extrahiere Status aus Log"""
    if not log_file or not log_file.exists():
        return {"status": "NOT_FOUND", "indicators": 0, "success": 0, "errors": 0}
    
    try:
        content = log_file.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        # Suche nach relevanten Zeilen
        total_inds = 0
        success_count = 0
        error_count = 0
        timeout_count = 0
        last_indicator = None
        
        for line in lines:
            if "Processing Indicator #" in line:
                match = re.search(r"Indicator #(\d+)", line)
                if match:
                    last_indicator = int(match.group(1))
                    total_inds += 1
            elif "SUCCESS" in line and "Indicator #" in line:
                success_count += 1
            elif "ERROR" in line or "FAILED" in line:
                error_count += 1
            elif "TIMEOUT" in line:
                timeout_count += 1
        
        # Letzte Zeile für Status
        last_line = lines[-1] if lines else ""
        is_running = "Processing" in last_line or "Starting" in last_line
        
        return {
            "status": "RUNNING" if is_running else "COMPLETED",
            "last_indicator": last_indicator,
            "total": total_inds,
            "success": success_count,
            "errors": error_count,
            "timeouts": timeout_count,
            "last_update": datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%H:%M:%S")
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def main():
    print("="*80)
    print("BACKTEST MONITOR - Alle laufenden Tests")
    print("="*80)
    print(f"Zeit: {datetime.now().strftime('%H:%M:%S')}\n")
    
    for name, pattern in LOG_PATTERNS.items():
        log_file = get_latest_log(pattern)
        status = parse_log_status(log_file)
        
        print(f"📊 {name}:")
        if log_file:
            print(f"   Log: {log_file.name}")
            print(f"   Status: {status.get('status', 'UNKNOWN')}")
            if status.get('last_indicator'):
                print(f"   Letzter Indikator: #{status['last_indicator']}")
            print(f"   Total: {status.get('total', 0)} | SUCCESS: {status.get('success', 0)} | ERRORS: {status.get('errors', 0)} | TIMEOUTS: {status.get('timeouts', 0)}")
            print(f"   Letzte Aktualisierung: {status.get('last_update', 'N/A')}")
        else:
            print(f"   ❌ Kein Log gefunden")
        print()
    
    print("="*80)
    print("Monitor läuft. Drücke Ctrl+C zum Beenden.")
    print("="*80)

if __name__ == "__main__":
    while True:
        try:
            main()
            time.sleep(30)  # Update alle 30 Sekunden
            print("\n" * 2)
        except KeyboardInterrupt:
            print("\n\nMonitor beendet.")
            break
