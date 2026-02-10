# -*- coding: utf-8 -*-
"""
QUICK BACKTEST - 102 PROBLEM STRATEGIEN
========================================
Daterange: 01.01.2024 - 01.06.2024
10 Minuten Sleep zwischen Indikatoren
Maximale Parallelisierung (6 Workers)
Detaillierte Log-Führung
"""

import sys
from pathlib import Path
import time
import pandas as pd
import numpy as np
import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

try:
    import vectorbt as vbt
except:
    print("[FATAL] vectorbt not installed!")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Backup_04" / "Unique"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
LOG_PATH = OUTPUT_PATH / "LOGS"
LOG_PATH.mkdir(parents=True, exist_ok=True)

# Lade 102 Problem-IDs
PROBLEM_IDS_FILE = BASE_PATH / "01_Backtest_System" / "Scripts" / "PROBLEM_AND_CLEAN_IDS.json"
with open(PROBLEM_IDS_FILE, 'r') as f:
    ids_data = json.load(f)
PROBLEM_IDS = ids_data['problem_ids']

TIMEFRAME = '1h'
FREQ = '1H'
SLIPPAGE_PIPS = 0.5
SPREADS = {'EUR_USD': 1.0, 'GBP_USD': 1.5, 'AUD_USD': 1.2, 'USD_CHF': 1.5, 'NZD_USD': 1.5, 'USD_CAD': 1.5}
SYMBOLS = ['EUR_USD', 'GBP_USD', 'AUD_USD', 'USD_CHF', 'NZD_USD', 'USD_CAD']

# QUICK TEST DATERANGE
DATE_START = '2024-01-01'
DATE_END = '2024-06-01'

# TRADING CONFIG
INITIAL_CAPITAL = 10000
LEVERAGE = 10
POSITION_SIZE = 100
INDICATOR_TIMEOUT = 900  # 15 Minuten
MAX_WORKERS = 6  # Maximale Parallelisierung
SLEEP_BETWEEN_INDICATORS = 600  # 10 Minuten Sleep

# SIMPLIFIED PARAMETERS (2 Combos max)
PERIOD_VALUES = [20, 50]
TP_SL_COMBOS = [(100, 50), (150, 75)]

# Log-Datei
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = LOG_PATH / f"quicktest_problem_102_{timestamp}.log"

def log(msg):
    """Log zu Datei und Console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

log("="*80)
log(f"QUICK BACKTEST - 102 PROBLEM STRATEGIEN")
log("="*80)
log(f"Daterange: {DATE_START} - {DATE_END}")
log(f"Problem-IDs: {len(PROBLEM_IDS)}")
log(f"Symbols: {len(SYMBOLS)}")
log(f"Workers: {MAX_WORKERS}")
log(f"Sleep: {SLEEP_BETWEEN_INDICATORS}s (10 Minuten)")
log(f"Timeout: {INDICATOR_TIMEOUT}s (15 Minuten)")
log(f"Log-Datei: {LOG_FILE}")
log("="*80)

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data():
    """Lade Marktdaten für alle Symbole"""
    log("Lade Marktdaten...")
    data = {}
    for symbol in SYMBOLS:
        csv_path = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
        if not csv_path.exists():
            log(f"[ERROR] Datei nicht gefunden: {csv_path}")
            continue
        
        df = pd.read_csv(csv_path)
        df['Time'] = pd.to_datetime(df['Time'])
        df = df.set_index('Time')
        df = df[(df.index >= DATE_START) & (df.index <= DATE_END)]
        
        if len(df) == 0:
            log(f"[WARNING] Keine Daten für {symbol} im Zeitraum {DATE_START} - {DATE_END}")
            continue
        
        data[symbol] = df
        log(f"  {symbol}: {len(df)} Kerzen geladen")
    
    log(f"Daten geladen: {len(data)} Symbole")
    return data

# ============================================================================
# INDICATOR LOADING
# ============================================================================

def load_indicator(ind_id):
    """Lade Indikator-Modul"""
    py_files = list(INDICATORS_PATH.glob(f"{ind_id:03d}_*.py"))
    if not py_files:
        return None, f"Datei nicht gefunden"
    
    py_file = py_files[0]
    try:
        spec = importlib.util.spec_from_file_location(f"indicator_{ind_id}", py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as e:
        return None, str(e)

# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signals(module, df, period):
    """Generiere Entry-Signale"""
    try:
        # Versuche calculate() Funktion
        if hasattr(module, 'calculate'):
            result = module.calculate(df, period=period)
            if isinstance(result, pd.DataFrame):
                if 'signal' in result.columns:
                    return result['signal']
                elif 'entry' in result.columns:
                    return result['entry']
        
        # Fallback: Erste Spalte verwenden
        if isinstance(result, pd.DataFrame) and len(result.columns) > 0:
            signals = result.iloc[:, 0]
            # Konvertiere zu 1/-1/0
            if signals.dtype == bool:
                return signals.astype(int)
            return signals
        
        return None
    except Exception as e:
        return None

# ============================================================================
# BACKTEST
# ============================================================================

def run_backtest(symbol, df, entries, tp_pips, sl_pips):
    """Führe VectorBT Backtest durch"""
    try:
        spread_pips = SPREADS.get(symbol, 1.0)
        total_cost_pips = spread_pips + SLIPPAGE_PIPS
        
        # Pip-Wert berechnen
        if 'JPY' in symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        tp_price = tp_pips * pip_value
        sl_price = sl_pips * pip_value
        
        # VectorBT Portfolio
        pf = vbt.Portfolio.from_signals(
            close=df['Close'],
            entries=entries > 0,
            exits=entries < 0,
            tp_stop=tp_price,
            sl_stop=sl_price,
            init_cash=INITIAL_CAPITAL,
            size=POSITION_SIZE,
            fees=total_cost_pips * pip_value,
            freq=FREQ
        )
        
        # Metriken
        total_return = pf.total_return()
        sharpe = pf.sharpe_ratio()
        max_dd = pf.max_drawdown()
        win_rate = pf.trades.win_rate()
        profit_factor = pf.trades.profit_factor()
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': pf.trades.count()
        }
    except Exception as e:
        return None

# ============================================================================
# TEST INDICATOR
# ============================================================================

def test_indicator(ind_id, data):
    """Teste einen Indikator"""
    start_time = time.time()
    log(f"\n{'='*80}")
    log(f"[START] Indikator #{ind_id:03d}")
    log(f"{'='*80}")
    
    # Lade Indikator
    module, error = load_indicator(ind_id)
    if error:
        log(f"[ERROR] Ind#{ind_id:03d}: Laden fehlgeschlagen - {error}")
        return {
            'ind_id': ind_id,
            'status': 'ERROR',
            'error': error,
            'duration': time.time() - start_time
        }
    
    log(f"[OK] Indikator #{ind_id:03d} geladen")
    
    # Teste alle Kombinationen
    results = []
    timeout_count = 0
    
    for period in PERIOD_VALUES:
        for tp_pips, sl_pips in TP_SL_COMBOS:
            combo_start = time.time()
            
            for symbol in SYMBOLS:
                if symbol not in data:
                    continue
                
                df = data[symbol]
                
                # Generiere Signale mit Timeout
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(generate_signals, module, df, period)
                        entries = future.result(timeout=60)  # 60s Timeout pro Symbol
                        
                        if entries is None or len(entries[entries != 0]) == 0:
                            continue
                        
                        # Backtest
                        metrics = run_backtest(symbol, df, entries, tp_pips, sl_pips)
                        if metrics and metrics['total_trades'] > 0:
                            results.append({
                                'symbol': symbol,
                                'period': period,
                                'tp_pips': tp_pips,
                                'sl_pips': sl_pips,
                                **metrics
                            })
                
                except TimeoutError:
                    timeout_count += 1
                    log(f"[TIMEOUT] Ind#{ind_id:03d} Period={period} TP={tp_pips} SL={sl_pips} Symbol={symbol}")
                except Exception as e:
                    log(f"[ERROR] Ind#{ind_id:03d} Period={period} Symbol={symbol}: {str(e)}")
            
            combo_duration = time.time() - combo_start
            if combo_duration > 60:
                log(f"[SLOW] Ind#{ind_id:03d} Period={period} TP={tp_pips} SL={sl_pips}: {combo_duration:.1f}s")
    
    # Zusammenfassung
    duration = time.time() - start_time
    
    if len(results) == 0:
        log(f"[NO RESULTS] Ind#{ind_id:03d}: Keine Ergebnisse nach {duration:.1f}s")
        if timeout_count > 0:
            log(f"[TIMEOUT] Ind#{ind_id:03d}: {timeout_count} Timeouts")
        return {
            'ind_id': ind_id,
            'status': 'NO_RESULTS',
            'timeout_count': timeout_count,
            'duration': duration
        }
    
    # Beste Ergebnisse
    best = max(results, key=lambda x: x.get('profit_factor', 0))
    
    log(f"[SUCCESS] Ind#{ind_id:03d}")
    log(f"  Ergebnisse: {len(results)}")
    log(f"  Timeouts: {timeout_count}")
    log(f"  Beste PF: {best['profit_factor']:.2f}")
    log(f"  Beste SR: {best['sharpe_ratio']:.2f}")
    log(f"  Symbol: {best['symbol']}")
    log(f"  Period: {best['period']}")
    log(f"  TP/SL: {best['tp_pips']}/{best['sl_pips']}")
    log(f"  Dauer: {duration:.1f}s")
    
    return {
        'ind_id': ind_id,
        'status': 'SUCCESS',
        'results_count': len(results),
        'timeout_count': timeout_count,
        'best_pf': best['profit_factor'],
        'best_sr': best['sharpe_ratio'],
        'best_symbol': best['symbol'],
        'best_period': best['period'],
        'best_tp_sl': f"{best['tp_pips']}/{best['sl_pips']}",
        'duration': duration
    }

# ============================================================================
# MAIN
# ============================================================================

def main():
    log("\n" + "="*80)
    log("START QUICK BACKTEST - 102 PROBLEM STRATEGIEN")
    log("="*80)
    
    # Lade Daten
    data = load_data()
    if len(data) == 0:
        log("[FATAL] Keine Daten geladen!")
        return
    
    # Teste alle Problem-Indikatoren
    all_results = []
    success_count = 0
    error_count = 0
    no_results_count = 0
    
    for i, ind_id in enumerate(PROBLEM_IDS, 1):
        log(f"\n{'='*80}")
        log(f"FORTSCHRITT: {i}/{len(PROBLEM_IDS)} ({i/len(PROBLEM_IDS)*100:.1f}%)")
        log(f"{'='*80}")
        
        result = test_indicator(ind_id, data)
        all_results.append(result)
        
        if result['status'] == 'SUCCESS':
            success_count += 1
        elif result['status'] == 'ERROR':
            error_count += 1
        elif result['status'] == 'NO_RESULTS':
            no_results_count += 1
        
        # Sleep zwischen Indikatoren (außer beim letzten)
        if i < len(PROBLEM_IDS):
            log(f"\n[SLEEP] 10 Minuten Pause...")
            time.sleep(SLEEP_BETWEEN_INDICATORS)
    
    # Finale Zusammenfassung
    log("\n" + "="*80)
    log("FINALE ZUSAMMENFASSUNG")
    log("="*80)
    log(f"Total getestet: {len(PROBLEM_IDS)}")
    log(f"SUCCESS: {success_count}")
    log(f"ERROR: {error_count}")
    log(f"NO RESULTS: {no_results_count}")
    log(f"Erfolgsquote: {success_count/len(PROBLEM_IDS)*100:.1f}%")
    
    # Speichere Ergebnisse
    results_file = OUTPUT_PATH / "Scripts" / f"quicktest_problem_102_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'summary': {
                'total': len(PROBLEM_IDS),
                'success': success_count,
                'error': error_count,
                'no_results': no_results_count
            },
            'results': all_results
        }, f, indent=2)
    
    log(f"\nErgebnisse gespeichert: {results_file}")
    log(f"Log-Datei: {LOG_FILE}")
    log("\n" + "="*80)
    log("QUICK BACKTEST ABGESCHLOSSEN")
    log("="*80)

if __name__ == "__main__":
    main()
