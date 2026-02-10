"""
PARALLEL DEBUGGER - Überwacht Backtest-Prozess
Analysiert Fehler und Warnings in Echtzeit
"""
import time
import json
from pathlib import Path
from datetime import datetime
import re

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
LOG_FILE = BASE_PATH / "REVERSE_BACKTEST_LOG.txt"
DEBUG_FILE = BASE_PATH / "DEBUG_ANALYSIS.txt"
CHECKPOINT_FILE = BASE_PATH / "REVERSE_CHECKPOINT.json"

def analyze_log():
    """Analysiere Log-Datei"""
    if not LOG_FILE.exists():
        return None
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Zähle Fehler und Warnings
    errors = [line for line in lines if '❌' in line or 'ERROR' in line.upper()]
    warnings = [line for line in lines if '⚠️' in line or 'WARNING' in line.upper()]
    success = [line for line in lines if '✅' in line and 'Return=' in line]
    
    # Extrahiere Metriken
    returns = []
    sharpes = []
    trades = []
    
    for line in success:
        # Return
        return_match = re.search(r'Return=([-\d.]+)%', line)
        if return_match:
            returns.append(float(return_match.group(1)))
        
        # Sharpe
        sharpe_match = re.search(r'Sharpe=([-\d.]+)', line)
        if sharpe_match:
            sharpes.append(float(sharpe_match.group(1)))
        
        # Trades
        trades_match = re.search(r'Trades=(\d+)', line)
        if trades_match:
            trades.append(int(trades_match.group(1)))
    
    return {
        'total_lines': len(lines),
        'errors': len(errors),
        'warnings': len(warnings),
        'success': len(success),
        'avg_return': sum(returns) / len(returns) if returns else 0,
        'avg_sharpe': sum(sharpes) / len(sharpes) if sharpes else 0,
        'avg_trades': sum(trades) / len(trades) if trades else 0,
        'error_lines': errors[-10:],  # Letzte 10 Fehler
        'warning_lines': warnings[-10:]  # Letzte 10 Warnings
    }

def load_checkpoint():
    """Lade Checkpoint"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return None

def write_debug_report(analysis, checkpoint):
    """Schreibe Debug-Report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
{'='*80}
DEBUG ANALYSIS REPORT - {timestamp}
{'='*80}

CHECKPOINT STATUS:
  Last Completed: #{checkpoint.get('last_completed_indicator', 'N/A')}
  Total Tested: {checkpoint.get('total_tested', 0)}
  Successful: {checkpoint.get('successful', 0)}
  Failed: {checkpoint.get('failed', 0)}
  Success Rate: {checkpoint.get('successful', 0)/(checkpoint.get('successful', 0)+checkpoint.get('failed', 1))*100:.1f}%

LOG ANALYSIS:
  Total Lines: {analysis['total_lines']}
  Errors: {analysis['errors']}
  Warnings: {analysis['warnings']}
  Successful Tests: {analysis['success']}

PERFORMANCE METRICS:
  Avg Return: {analysis['avg_return']:.2f}%
  Avg Sharpe: {analysis['avg_sharpe']:.2f}
  Avg Trades: {analysis['avg_trades']:.0f}

RECENT ERRORS:
"""
    
    for error in analysis['error_lines']:
        report += f"  {error}"
    
    report += "\nRECENT WARNINGS:\n"
    for warning in analysis['warning_lines']:
        report += f"  {warning}"
    
    report += "\n" + "="*80 + "\n"
    
    with open(DEBUG_FILE, 'a', encoding='utf-8') as f:
        f.write(report)
    
    return report

def main():
    """Hauptfunktion - Parallel-Debugger"""
    print("="*80)
    print("🔍 PARALLEL DEBUGGER GESTARTET")
    print("="*80)
    print("Überwacht Backtest-Prozess in Echtzeit...")
    print("Drücke Ctrl+C zum Beenden\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            # Analysiere Log
            analysis = analyze_log()
            checkpoint = load_checkpoint()
            
            if analysis and checkpoint:
                # Schreibe Report
                report = write_debug_report(analysis, checkpoint)
                
                # Console Output (alle 10 Iterationen)
                if iteration % 10 == 0:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] DEBUG UPDATE #{iteration}")
                    print(f"  Progress: Ind#{checkpoint.get('last_completed_indicator', 'N/A')}")
                    print(f"  Success: {checkpoint.get('successful', 0)}/{checkpoint.get('total_tested', 0)}")
                    print(f"  Errors: {analysis['errors']}, Warnings: {analysis['warnings']}")
                    print(f"  Avg Return: {analysis['avg_return']:.2f}%, Sharpe: {analysis['avg_sharpe']:.2f}")
            
            # Warte 30 Sekunden
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Debugger gestoppt")
        print("="*80)

if __name__ == "__main__":
    main()
