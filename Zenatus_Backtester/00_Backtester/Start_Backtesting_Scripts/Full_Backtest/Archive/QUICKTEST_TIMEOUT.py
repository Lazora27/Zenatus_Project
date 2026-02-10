# -*- coding: utf-8 -*-
"""
QUICKTEST FÜR TIMEOUT-INDIKATOREN
===================================
18 Indikatoren mit VectorBT Timeouts
1 Jahr Daten (2024-01-01 bis 2025-01-01)
1h Timeframe
10 Minuten Sleep pro Indikator
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
import threading
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
PARAM_CONFIGS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Indicator_Configs"
ANALYSIS_JSON = BASE_PATH / "01_Backtest_System" / "Scripts" / "INDICATORS_PROBLEM_2COMBOS.json"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data" / "1h"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
LOG_PATH = OUTPUT_PATH / "LOGS"
LOG_PATH.mkdir(parents=True, exist_ok=True)

# QUICKTEST CONFIG
TIMEFRAME = '1h'
FREQ = '1H'
SLIPPAGE_PIPS = 0.5
SPREADS = {'EUR_USD': 1.0, 'GBP_USD': 1.5, 'AUD_USD': 1.2, 'USD_CHF': 1.5, 'NZD_USD': 1.5, 'USD_CAD': 1.5}
SYMBOLS = ['EUR_USD', 'GBP_USD', 'AUD_USD', 'USD_CHF', 'NZD_USD', 'USD_CAD']

# 1 JAHR DATEN
DATE_START = '2024-01-01'
DATE_END = '2025-01-01'

# TRADING CONFIG
INITIAL_CAPITAL = 10000
LEVERAGE = 10
POSITION_SIZE = 100
INDICATOR_TIMEOUT = 900  # 15 Minuten
MAX_WORKERS = 6  # 6 parallel
SLEEP_BETWEEN_INDICATORS = 600  # 10 Minuten Sleep

# TIMEOUT-INDIKATOREN (18 total)
TIMEOUT_INDICATORS = [369, 370, 371, 374, 376, 471, 478, 552, 553, 554, 555, 561, 562, 563, 564, 565, 566, 567]

# FALLBACK PARAMETERS
FALLBACK_PERIOD_VALUES = [10, 20, 30]
FALLBACK_TP_SL_COMBOS = [(50, 30), (75, 40), (100, 50)]
MAX_COMBINATIONS_PER_SYMBOL = 500

print("="*80)
print(f"QUICKTEST TIMEOUT-INDIKATOREN - {TIMEFRAME.upper()}")
print("="*80)
print(f"Timeout-Indikatoren: {len(TIMEOUT_INDICATORS)}")
print(f"Datum: {DATE_START} bis {DATE_END} (1 Jahr)")
print(f"Sleep: {SLEEP_BETWEEN_INDICATORS//60} Minuten pro Indikator")
print(f"Timeout: {INDICATOR_TIMEOUT}s pro Indikator")
print(f"MAX_WORKERS: {MAX_WORKERS}")
print("="*80)

# ============================================================================
# LOGGING
# ============================================================================

LOG_FILE = LOG_PATH / f"quicktest_timeout_{TIMEFRAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def log_message(msg, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_line = f"[{timestamp}] [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

log_message("Quicktest System gestartet")

# ============================================================================
# DATA LOADING
# ============================================================================

DATA_CACHE = {}
pip_value = 0.0001

print("\nLoading data...")
for symbol in SYMBOLS:
    # CSVs liegen in Unterordnern: Market_Data/1h/EUR_USD/EUR_USD_aggregated.csv
    csv_file = DATA_PATH / symbol / f"{symbol}_aggregated.csv"
    if not csv_file.exists():
        log_message(f"{symbol}: CSV nicht gefunden: {csv_file}", "ERROR")
        continue
    
    df = pd.read_csv(csv_file)
    # CSV hat 'Time' statt 'time' (Großbuchstabe)
    df['Time'] = pd.to_datetime(df['Time'])
    df = df.set_index('Time')
    df = df.sort_index()
    df.columns = df.columns.str.lower()  # Konvertiere alle Spalten zu lowercase
    
    # Filter auf 1 Jahr
    df_filtered = df[(df.index >= DATE_START) & (df.index < DATE_END)]
    
    DATA_CACHE[symbol] = {
        'full': df_filtered
    }
    
    print(f"  {symbol}: {len(df_filtered)} bars loaded")

# ============================================================================
# PARAMETER LOADING
# ============================================================================

def load_parameter_config(ind_num: int, ind_name: str) -> dict:
    """Lädt Parameter-Config für Indikator"""
    # Versuche Analysis JSON
    if ANALYSIS_JSON.exists():
        try:
            with open(ANALYSIS_JSON, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            if str(ind_num) in analysis:
                ind_data = analysis[str(ind_num)]
                optimal_inputs = ind_data.get('optimal_inputs', {})
                
                entry_param_combos = {}
                for param_name, param_config in optimal_inputs.items():
                    if param_name not in ['tp_pips', 'sl_pips']:
                        if 'values' in param_config:
                            entry_param_combos[param_name] = param_config['values']
                
                tp_values = optimal_inputs.get('tp_pips', {}).get('values', [])
                sl_values = optimal_inputs.get('sl_pips', {}).get('values', [])
                
                if entry_param_combos or (tp_values and sl_values):
                    if not entry_param_combos:
                        entry_param_combos = {'period': [10, 20, 30]}
                    
                    if not tp_values or not sl_values:
                        tp_values = [50, 75, 100]
                        sl_values = [30, 40, 50]
                    
                    tp_sl_combos = [(tp, sl) for tp in tp_values for sl in sl_values if tp > sl]
                    
                    log_message(f"Ind#{ind_num}: Analysis JSON - {len(entry_param_combos)} entry params, {len(tp_sl_combos)} TP/SL", "INFO")
                    
                    return {
                        'period_values': entry_param_combos.get('period', list(entry_param_combos.values())[0] if entry_param_combos else [20]),
                        'entry_param_combos': entry_param_combos,
                        'tp_sl_combos': tp_sl_combos[:15] if len(tp_sl_combos) > 15 else tp_sl_combos,
                        'indicator_type': ind_data.get('class_structure', 'unknown')
                    }
        except Exception as e:
            log_message(f"Ind#{ind_num}: Fehler Analysis JSON: {str(e)[:100]}", "WARNING")
    
    # Fallback
    log_message(f"Ind#{ind_num}: Fallback-Parameter", "WARNING")
    return {
        'period_values': FALLBACK_PERIOD_VALUES,
        'entry_param_combos': {'period': FALLBACK_PERIOD_VALUES},
        'tp_sl_combos': FALLBACK_TP_SL_COMBOS,
        'indicator_type': 'fallback'
    }

# ============================================================================
# METRICS CALCULATION
# ============================================================================

def calculate_metrics(pf, spread_pips, tp_pips, sl_pips):
    """Berechnet Metriken aus VectorBT Portfolio"""
    try:
        net_return = pf.total_return() * 100
        max_dd = abs(pf.max_drawdown()) * 100
        daily_dd = abs(pf.drawdown().max()) * 100
        trades = pf.trades.count()
        
        if trades == 0:
            return None
        
        win_rate = pf.trades.win_rate() * 100
        
        winning_trades = pf.trades.winning
        losing_trades = pf.trades.losing
        
        gross_wins = winning_trades.pnl.sum() if winning_trades.count() > 0 else 0.0
        gross_losses = abs(losing_trades.pnl.sum()) if losing_trades.count() > 0 else 0.0
        
        if gross_losses > 0:
            profit_factor = gross_wins / gross_losses
        else:
            profit_factor = gross_wins if gross_wins > 0 else 0.0
        
        sharpe = pf.sharpe_ratio()
        
        if np.isnan(profit_factor) or np.isinf(profit_factor):
            profit_factor = 0.0
        if np.isnan(sharpe) or np.isinf(sharpe):
            sharpe = 0.0
        
        return {
            'Total_Return': float(f"{net_return:.4f}"),
            'Max_Drawdown': float(f"{max_dd:.4f}"),
            'Win_Rate_%': float(f"{win_rate:.2f}"),
            'Total_Trades': int(trades),
            'Profit_Factor': float(f"{profit_factor:.2f}"),
            'Sharpe_Ratio': float(f"{sharpe:.2f}"),
            'TP_Pips': int(tp_pips),
            'SL_Pips': int(sl_pips)
        }
    except Exception as e:
        return None

# ============================================================================
# BACKTEST FUNCTION
# ============================================================================

def run_backtest_single(df, entries, tp_pips, sl_pips, spread_pips):
    """Single backtest mit Timeout"""
    try:
        effective_tp = (tp_pips - spread_pips - SLIPPAGE_PIPS) * pip_value
        effective_sl = (sl_pips + spread_pips + SLIPPAGE_PIPS) * pip_value
        
        if effective_tp <= 0 or effective_sl <= 0:
            return None
        
        pf = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries,
            exits=False,
            tp_stop=effective_tp,
            sl_stop=effective_sl,
            init_cash=INITIAL_CAPITAL,
            size=POSITION_SIZE,
            size_type='amount',
            fees=0.0,
            freq=FREQ
        )
        
        return calculate_metrics(pf, spread_pips, tp_pips, sl_pips)
    except Exception as e:
        return None

# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================

def test_indicator(ind_file):
    ind_name = ind_file.stem
    try:
        ind_num = int(ind_name.split('_')[0])
    except:
        log_message(f"Fehler beim Extrahieren der Indikator-Nummer: {ind_name}", "ERROR")
        return None
    
    if ind_num not in TIMEOUT_INDICATORS:
        return None
    
    start_time = time.time()
    
    param_config = load_parameter_config(ind_num, ind_name)
    entry_param_combos = param_config['entry_param_combos']
    tp_sl_combos = param_config['tp_sl_combos']
    
    try:
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        class_name = None
        for attr in dir(module):
            if attr.startswith('_'):
                continue
            obj = getattr(module, attr)
            if isinstance(obj, type):
                if 'Indicator' in attr or hasattr(obj, 'calculate') or hasattr(obj, 'generate_signals') or hasattr(obj, 'generate_signals_fixed'):
                    class_name = attr
                    break
        
        if not class_name:
            log_message(f"Ind#{ind_num}: Keine Indikator-Klasse gefunden", "ERROR")
            return ('ERROR', ind_num, 0)
        
        ind_instance = getattr(module, class_name)()
        
        all_combo_results = []
        timeout_count = 0
        
        for symbol in SYMBOLS:
            if symbol not in DATA_CACHE:
                continue
            
            spread_pips = SPREADS.get(symbol, 2.0)
            df_full = DATA_CACHE[symbol]['full']
            
            # Test nur erste 3 Entry-Parameter
            param_names = list(entry_param_combos.keys())
            if len(param_names) > 0:
                first_param = param_names[0]
                test_values = entry_param_combos[first_param][:3]  # Nur 3 Werte
                
                for val in test_values:
                    entry_params_dict = {first_param: val}
                    
                    # Generate signals mit Timeout
                    exception_container = [None]
                    result_container = [None]
                    
                    def run_signal_gen():
                        try:
                            if hasattr(ind_instance, 'generate_signals_fixed'):
                                result_container[0] = ind_instance.generate_signals_fixed(df_full, **entry_params_dict)
                            elif hasattr(ind_instance, 'generate_signals'):
                                result_container[0] = ind_instance.generate_signals(df_full, **entry_params_dict)
                            elif hasattr(ind_instance, 'calculate'):
                                result_container[0] = ind_instance.calculate(df_full, **entry_params_dict)
                        except Exception as e:
                            exception_container[0] = e
                    
                    thread = threading.Thread(target=run_signal_gen)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=60)
                    
                    if thread.is_alive():
                        log_message(f"Ind#{ind_num} {symbol} Entry {entry_params_dict}: VectorBT TIMEOUT nach 60s", "WARNING")
                        timeout_count += 1
                        continue
                    
                    if exception_container[0]:
                        continue
                    
                    signals = result_container[0]
                    if signals is None or len(signals) == 0:
                        continue
                    
                    entries = signals > 0
                    
                    # Test nur erste 2 TP/SL Combos
                    for tp_pips, sl_pips in tp_sl_combos[:2]:
                        metrics = run_backtest_single(df_full, entries, tp_pips, sl_pips, spread_pips)
                        if metrics:
                            all_combo_results.append({
                                'Symbol': symbol,
                                'Entry_Params': str(entry_params_dict),
                                **metrics
                            })
        
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        
        if len(all_combo_results) > 0:
            avg_pf = np.mean([r['Profit_Factor'] for r in all_combo_results])
            avg_sr = np.mean([r['Sharpe_Ratio'] for r in all_combo_results])
            log_message(f"Ind#{ind_num} {ind_name} - SUCCESS: {len(all_combo_results)} combos, PF={avg_pf:.2f}, SR={avg_sr:.2f}, Timeouts={timeout_count}", "SUCCESS")
            return ('SUCCESS', ind_num, timeout_count)
        else:
            log_message(f"Ind#{ind_num} {ind_name} - KEINE ERGEBNISSE (Timeouts={timeout_count})", "ERROR")
            return ('ERROR', ind_num, timeout_count)
        
    except Exception as e:
        elapsed = time.time() - start_time
        log_message(f"Ind#{ind_num} {ind_name} - FEHLER: {str(e)[:200]}", "ERROR")
        return ('ERROR', ind_num, 0)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_message("="*80)
log_message(f"QUICKTEST START - {TIMEFRAME}")
log_message("="*80)

all_indicators = sorted(INDICATORS_PATH.glob("*.py"), reverse=True)
test_indicators = [ind for ind in all_indicators if int(ind.stem.split('_')[0]) in TIMEOUT_INDICATORS]

log_message(f"Zu testen: {len(test_indicators)} Timeout-Indikatoren")
log_message("")

start_time = time.time()

results = {
    'SUCCESS': [],
    'ERROR': [],
    'TIMEOUT_COUNTS': {}
}

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(test_indicator, ind_file): ind_file for ind_file in test_indicators}
    
    completed_count = 0
    for future in as_completed(futures):
        try:
            result = future.result(timeout=INDICATOR_TIMEOUT)
            if result:
                status, ind_num, timeout_count = result
                results[status].append(ind_num)
                results['TIMEOUT_COUNTS'][ind_num] = timeout_count
                
                completed_count += 1
                # 10 Minuten Sleep nach jedem Indikator
                if completed_count < len(test_indicators):
                    sleep_min = SLEEP_BETWEEN_INDICATORS // 60
                    log_message(f"Sleep {sleep_min} Minuten vor nächstem Indikator...", "INFO")
                    time.sleep(SLEEP_BETWEEN_INDICATORS)
        except TimeoutError:
            ind_file = futures[future]
            log_message(f"[TIMEOUT] {ind_file.stem} exceeded {INDICATOR_TIMEOUT}s", "ERROR")
        except Exception as e:
            log_message(f"[ERROR] {str(e)[:50]}", "ERROR")

elapsed = time.time() - start_time
elapsed_hours = int(elapsed // 3600)
elapsed_min = int((elapsed % 3600) // 60)

log_message("="*80)
log_message(f"QUICKTEST COMPLETE!")
log_message(f"Total time: {elapsed_hours:02d}:{elapsed_min:02d}")
log_message(f"SUCCESS: {len(results['SUCCESS'])}")
log_message(f"ERROR: {len(results['ERROR'])}")
log_message(f"SUCCESS IDs: {sorted(results['SUCCESS'])}")
log_message(f"ERROR IDs: {sorted(results['ERROR'])}")
log_message("="*80)

# Save results
results_file = OUTPUT_PATH / "Scripts" / "QUICKTEST_TIMEOUT_RESULTS.json"
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)

log_message(f"Results saved to: {results_file}")
