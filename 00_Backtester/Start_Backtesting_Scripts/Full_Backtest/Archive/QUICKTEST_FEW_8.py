# -*- coding: utf-8 -*-
"""
QUICKTEST - PIPELINE VALIDATION
================================
Testet ALLE 383 Indikatoren (1-466, ohne 8) mit nur 2 Kombinationen pro Indikator
Ziel: Schnelle Validierung welche Indikatoren funktionieren
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
QUICKTEST_JSON = BASE_PATH / "01_Backtest_System" / "Scripts" / "QUICKTEST_FEW_8.json"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
LOG_PATH = OUTPUT_PATH / "LOGS"
LOG_PATH.mkdir(parents=True, exist_ok=True)

TIMEFRAME = '1h'
FREQ = '1H'
SYMBOLS = ['EUR_USD', 'GBP_USD', 'AUD_USD', 'USD_CHF', 'NZD_USD', 'USD_CAD']
DATE_START = '2020-01-01'
DATE_END = '2025-09-20'

# QUICKTEST: Nur 2 Kombinationen pro Indikator
QUICKTEST_MODE = True
MAX_WORKERS = 10  # Mehr Workers für schnelleren Test
INDICATOR_TIMEOUT = 240  # 4 Minuten pro Indikator (verdoppelt)

# TRADING CONFIG
INITIAL_CAPITAL = 10000
LEVERAGE = 10
POSITION_SIZE = 100
SLIPPAGE_PIPS = 0.5
SPREADS = {'EUR_USD': 1.0, 'GBP_USD': 1.5, 'AUD_USD': 1.2, 'USD_CHF': 1.5, 'NZD_USD': 1.5, 'USD_CAD': 1.5}
COMMISSION_PER_LOT = 7.0
pip_value = 0.0001

print("="*80)
print(f"QUICKTEST FEW_8 - {TIMEFRAME.upper()}")
print("="*80)
print(f"Testing: 8 FEW_SIGNALS Indicators")
print("="*80)
print(f"Date: {DATE_START} to {DATE_END}")
print(f"Symbols: {len(SYMBOLS)}")
print(f"Mode: QUICKTEST (2 combos per indicator)")
print(f"Workers: {MAX_WORKERS}")
print(f"Timeout: {INDICATOR_TIMEOUT}s")
print("="*80)

# ============================================================================
# LOGGING
# ============================================================================

LOG_FILE = LOG_PATH / f"quicktest_few_8_{TIMEFRAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def log_message(message, level='INFO'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

log_message("Quicktest System gestartet", "INFO")

# ============================================================================
# DATA LOADING
# ============================================================================

print("\nLoading data...")
DATA_CACHE = {}

for symbol in SYMBOLS:
    csv_path = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
    if not csv_path.exists():
        print(f"  {symbol}: NOT FOUND")
        continue
    
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    df = df[(df.index >= DATE_START) & (df.index <= DATE_END)]
    
    DATA_CACHE[symbol] = {'full': df}
    print(f"  {symbol}: {len(df)} bars loaded")

# ============================================================================
# LOAD QUICKTEST PARAMS
# ============================================================================

log_message("Loading Quicktest Parameters", "INFO")
with open(QUICKTEST_JSON, 'r', encoding='utf-8') as f:
    QUICKTEST_PARAMS = json.load(f)

log_message(f"Loaded {len(QUICKTEST_PARAMS)} indicators for quicktest", "INFO")

# ============================================================================
# BACKTEST FUNCTIONS
# ============================================================================

def calculate_metrics(pf, spread_pips, tp_pips, sl_pips):
    """Berechnet Basis-Metriken für Quicktest"""
    trades = pf.trades.count()
    if trades < 3:
        return None
    
    total_profit = pf.total_profit()
    lot_size = POSITION_SIZE / 100000
    total_commission = trades * COMMISSION_PER_LOT * lot_size
    net_profit = total_profit - total_commission
    net_return = (net_profit / INITIAL_CAPITAL) * 100
    
    equity = pf.value()
    cummax = equity.expanding().max()
    drawdowns = (equity - cummax) / cummax
    max_dd = abs(drawdowns.min()) * 100
    
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
        'Profit_Factor': float(f"{profit_factor:.3f}"),
        'Sharpe_Ratio': float(f"{sharpe:.3f}"),
        'TP_Pips': tp_pips,
        'SL_Pips': sl_pips
    }

def backtest_single(df, entries, tp_pips, sl_pips, spread_pips):
    """Single backtest mit Timeout-Protection"""
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
# TEST INDICATOR FUNCTION
# ============================================================================

def test_indicator_quick(ind_num):
    """Quicktest: Nur 2 Kombinationen pro Indikator"""
    
    if str(ind_num) not in QUICKTEST_PARAMS:
        return None
    
    params = QUICKTEST_PARAMS[str(ind_num)]
    ind_file = INDICATORS_PATH / params['file']
    ind_name = ind_file.stem
    
    if not ind_file.exists():
        log_message(f"Ind#{ind_num}: File not found", "ERROR")
        return None
    
    start_time = time.time()
    
    try:
        # Load Indicator
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        class_name = params.get('class_name')
        if not class_name or not hasattr(module, class_name):
            # Fallback: Suche Klasse
            for attr in dir(module):
                if attr.startswith('_'):
                    continue
                obj = getattr(module, attr)
                if isinstance(obj, type) and (hasattr(obj, 'generate_signals_fixed') or 'Indicator' in attr):
                    class_name = attr
                    break
        
        if not class_name:
            log_message(f"Ind#{ind_num}: No class found", "ERROR")
            return None
        
        ind_instance = getattr(module, class_name)()
        
        # Extract first 2 combinations from QUICKTEST_PARAMS
        optimal_inputs = params['optimal_inputs']
        
        # Get first entry parameter combo
        entry_params = {}
        for param_name, param_config in optimal_inputs.items():
            if param_name not in ['tp_pips', 'sl_pips']:
                values = param_config.get('values', [])
                if len(values) >= 1:
                    entry_params[param_name] = values[0]  # Nur erste Value
        
        # Get first 2 TP/SL combos
        tp_values = optimal_inputs.get('tp_pips', {}).get('values', [50, 100])[:2]
        sl_values = optimal_inputs.get('sl_pips', {}).get('values', [30, 50])[:2]
        
        if not tp_values or not sl_values:
            tp_values = [50, 100]
            sl_values = [30, 50]
        
        tp_sl_combos = [(tp_values[0], sl_values[0])]
        if len(tp_values) > 1 and len(sl_values) > 1:
            tp_sl_combos.append((tp_values[1], sl_values[1]))
        
        results = []
        success_count = 0
        timeout_count = 0
        error_count = 0
        
        # Test auf 1 Symbol (EUR_USD) für Quicktest
        symbol = 'EUR_USD'
        if symbol not in DATA_CACHE:
            return None
        
        df_full = DATA_CACHE[symbol]['full']
        spread_pips = SPREADS.get(symbol, 2.0)
        
        # Generate signals mit Timeout
        try:
            import threading
            result_container = [None]
            exception_container = [None]
            
            def run_signals():
                try:
                    result_container[0] = ind_instance.generate_signals_fixed(df_full, entry_params)
                except Exception as e:
                    exception_container[0] = e
            
            thread = threading.Thread(target=run_signals)
            thread.daemon = True
            thread.start()
            thread.join(timeout=30)
            
            if thread.is_alive():
                timeout_count += 1
                log_message(f"Ind#{ind_num}: Signal generation TIMEOUT", "WARNING")
                return {'ind_num': ind_num, 'status': 'TIMEOUT_SIGNALS', 'elapsed': time.time() - start_time}
            
            if exception_container[0]:
                raise exception_container[0]
            
            signals_full = result_container[0]
            
            if signals_full is None:
                error_count += 1
                return {'ind_num': ind_num, 'status': 'ERROR_SIGNALS', 'elapsed': time.time() - start_time}
            
        except Exception as e:
            error_count += 1
            log_message(f"Ind#{ind_num}: Signal error - {str(e)[:100]}", "ERROR")
            return {'ind_num': ind_num, 'status': 'ERROR_SIGNALS', 'error': str(e)[:100], 'elapsed': time.time() - start_time}
        
        entries_full = signals_full['entries'].values
        if isinstance(entries_full, np.ndarray):
            entries_full = pd.Series(entries_full, index=df_full.index)
        entries_full = entries_full.fillna(False).astype(bool)
        
        if entries_full.sum() < 3:
            log_message(f"Ind#{ind_num}: Too few signals ({entries_full.sum()})", "WARNING")
            return {'ind_num': ind_num, 'status': 'FEW_SIGNALS', 'signals': int(entries_full.sum()), 'elapsed': time.time() - start_time}
        
        # Test 2 TP/SL Kombinationen
        for tp_pips, sl_pips in tp_sl_combos:
            try:
                import threading
                result_container = [None]
                exception_container = [None]
                
                def run_backtest():
                    try:
                        result_container[0] = backtest_single(df_full, entries_full, tp_pips, sl_pips, spread_pips)
                    except Exception as e:
                        exception_container[0] = e
                
                thread = threading.Thread(target=run_backtest)
                thread.daemon = True
                thread.start()
                thread.join(timeout=30)
                
                if thread.is_alive():
                    timeout_count += 1
                    log_message(f"Ind#{ind_num}: Backtest TIMEOUT (TP={tp_pips}, SL={sl_pips})", "WARNING")
                    continue
                
                if exception_container[0]:
                    raise exception_container[0]
                
                metrics = result_container[0]
                
                if metrics:
                    success_count += 1
                    results.append(metrics)
                
            except Exception as e:
                error_count += 1
                log_message(f"Ind#{ind_num}: Backtest error - {str(e)[:100]}", "ERROR")
                continue
        
        elapsed = time.time() - start_time
        
        if success_count > 0:
            best = max(results, key=lambda x: x['Sharpe_Ratio'])
            log_message(f"Ind#{ind_num:03d} {ind_name[:30]:30s} - SUCCESS: {success_count}/2 combos, PF={best['Profit_Factor']:.2f}, SR={best['Sharpe_Ratio']:.2f}, {elapsed:.1f}s", "SUCCESS")
            return {'ind_num': ind_num, 'status': 'SUCCESS', 'combos': success_count, 'best_pf': best['Profit_Factor'], 'best_sr': best['Sharpe_Ratio'], 'elapsed': elapsed}
        elif timeout_count > 0:
            log_message(f"Ind#{ind_num:03d} {ind_name[:30]:30s} - TIMEOUT: {timeout_count} timeouts, {elapsed:.1f}s", "WARNING")
            return {'ind_num': ind_num, 'status': 'TIMEOUT', 'timeouts': timeout_count, 'elapsed': elapsed}
        else:
            log_message(f"Ind#{ind_num:03d} {ind_name[:30]:30s} - FAILED: {error_count} errors, {elapsed:.1f}s", "ERROR")
            return {'ind_num': ind_num, 'status': 'FAILED', 'errors': error_count, 'elapsed': elapsed}
    
    except Exception as e:
        log_message(f"Ind#{ind_num}: Fatal error - {str(e)[:100]}", "ERROR")
        return {'ind_num': ind_num, 'status': 'FATAL_ERROR', 'error': str(e)[:100], 'elapsed': time.time() - start_time}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_message("Starting Quicktest...", "INFO")
start_time = time.time()

# Get all indicator numbers from QUICKTEST_PARAMS
indicator_nums = sorted([int(k) for k in QUICKTEST_PARAMS.keys()])

log_message(f"Testing {len(indicator_nums)} indicators", "INFO")

results_summary = {
    'SUCCESS': [],
    'TIMEOUT': [],
    'TIMEOUT_SIGNALS': [],
    'FAILED': [],
    'ERROR_SIGNALS': [],
    'FEW_SIGNALS': [],
    'FATAL_ERROR': []
}

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(test_indicator_quick, ind_num): ind_num for ind_num in indicator_nums}
    
    for future in as_completed(futures):
        try:
            result = future.result(timeout=INDICATOR_TIMEOUT)
            if result:
                status = result['status']
                results_summary[status].append(result['ind_num'])
        except TimeoutError:
            ind_num = futures[future]
            log_message(f"Ind#{ind_num}: EXECUTOR TIMEOUT", "ERROR")
            results_summary['TIMEOUT'].append(ind_num)
        except Exception as e:
            ind_num = futures[future]
            log_message(f"Ind#{ind_num}: Executor error - {str(e)[:100]}", "ERROR")
            results_summary['FATAL_ERROR'].append(ind_num)

elapsed = time.time() - start_time
elapsed_min = int(elapsed // 60)
elapsed_sec = int(elapsed % 60)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*80)
print("QUICKTEST COMPLETE!")
print("="*80)
print(f"Total time: {elapsed_min:02d}:{elapsed_sec:02d}")
print(f"\nRESULTS:")
print(f"  ✅ SUCCESS:         {len(results_summary['SUCCESS']):3d} indicators")
print(f"  ⏱️  TIMEOUT:         {len(results_summary['TIMEOUT']):3d} indicators")
print(f"  ⏱️  TIMEOUT_SIGNALS: {len(results_summary['TIMEOUT_SIGNALS']):3d} indicators")
print(f"  ⚠️  FEW_SIGNALS:    {len(results_summary['FEW_SIGNALS']):3d} indicators")
print(f"  ❌ FAILED:          {len(results_summary['FAILED']):3d} indicators")
print(f"  ❌ ERROR_SIGNALS:   {len(results_summary['ERROR_SIGNALS']):3d} indicators")
print(f"  ❌ FATAL_ERROR:     {len(results_summary['FATAL_ERROR']):3d} indicators")
print("="*80)

# Save results
results_file = OUTPUT_PATH / "QUICKTEST_RESULTS.json"
with open(results_file, 'w', encoding='utf-8') as f:
    json.dump(results_summary, f, indent=2)

log_message(f"Results saved to: {results_file}", "INFO")
log_message(f"Quicktest complete: {len(results_summary['SUCCESS'])} successful indicators", "SUCCESS")

print(f"\n✅ SUCCESSFUL INDICATORS ({len(results_summary['SUCCESS'])}):")
for ind_num in sorted(results_summary['SUCCESS'])[:20]:
    print(f"  - Ind#{ind_num:03d}")
if len(results_summary['SUCCESS']) > 20:
    print(f"  ... and {len(results_summary['SUCCESS']) - 20} more")

print(f"\n⏱️ TIMEOUT INDICATORS ({len(results_summary['TIMEOUT']) + len(results_summary['TIMEOUT_SIGNALS'])}):")
timeout_all = sorted(results_summary['TIMEOUT'] + results_summary['TIMEOUT_SIGNALS'])
for ind_num in timeout_all[:20]:
    print(f"  - Ind#{ind_num:03d}")
if len(timeout_all) > 20:
    print(f"  ... and {len(timeout_all) - 20} more")
