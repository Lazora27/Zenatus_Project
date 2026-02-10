"""
QUICK TEST - 5 INDIKATOREN
Testet: Geschwindigkeit, Robustheit, Dokumentation, CSV-Output, Logs
Output: 98_Quicktest/
"""

import sys
from pathlib import Path
import time
import pandas as pd
import numpy as np
import importlib.util
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
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
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Production_595_Ultimate"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "98_Quicktest"
LOG_PATH = OUTPUT_PATH / "LOGS"

sys.path.insert(0, str(INDICATORS_PATH))

# Test Configuration
TIMEFRAME = '1h'
SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_JPY']  # 3 Symbole für schnelleren Test
DATE_START = '2020-01-01'
DATE_END = '2025-09-20'
TEST_START = '2024-06-01'

# Trading Config
INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
SLIPPAGE_PIPS = 1.0
pip_value = 0.0001
FREQ = '1h'

SPREADS = {
    'EUR_USD': 1.8,
    'GBP_USD': 2.2,
    'USD_JPY': 1.9,
    'AUD_USD': 2.0,
    'USD_CAD': 2.1,
    'NZD_USD': 2.3
}

# Test nur 10 TP/SL Combos für Geschwindigkeit
TP_SL_COMBOS = [
    (50, 25), (75, 35), (100, 50), (125, 60), (150, 75),
    (175, 85), (200, 100), (225, 110), (250, 125), (300, 150)
]

PERIOD_VALUES = [20, 50]  # Nur 2 Perioden für schnelleren Test

# Test diese 5 Indikatoren
TEST_INDICATORS = [
    '001_trend_sma.py',
    '002_trend_ema.py',
    '041_trend_rsi.py',
    '042_trend_macd.py',
    '043_trend_bollinger.py'
]

INDICATOR_TIMEOUT = 300
MAX_WORKERS = 2  # Nur 2 Workers für Test

# ============================================================================
# SETUP
# ============================================================================

# Create output directories
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
LOG_PATH.mkdir(parents=True, exist_ok=True)
(OUTPUT_PATH / "Documentation").mkdir(exist_ok=True)
(OUTPUT_PATH / "Documentation" / "Fixed_Exit").mkdir(exist_ok=True)
(OUTPUT_PATH / "Documentation" / "Fixed_Exit" / TIMEFRAME).mkdir(exist_ok=True)

# Setup logging
log_file = LOG_PATH / f"QUICKTEST_5IND_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def log(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

print("="*80)
print("QUICK TEST - 5 INDIKATOREN")
print("="*80)
print(f"Date: {DATE_START} to {DATE_END}")
print(f"Train: {DATE_START} to {TEST_START} (80%)")
print(f"Test:  {TEST_START} to {DATE_END} (20%)")
print(f"Symbols: {len(SYMBOLS)}")
print(f"Indicators: {len(TEST_INDICATORS)}")
print(f"Period Values: {PERIOD_VALUES}")
print(f"TP/SL Combos: {len(TP_SL_COMBOS)}")
print(f"Output: {OUTPUT_PATH}")
print("="*80)

log("="*80)
log("QUICK TEST START")
log("="*80)

# ============================================================================
# DATA LOADING
# ============================================================================

print("\nLoading data...")
log("Loading data...")

DATA_CACHE = {}

for symbol in SYMBOLS:
    try:
        df = pd.read_csv(DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv")
        df['Time'] = pd.to_datetime(df['Time'])
        df.set_index('Time', inplace=True)
        df = df[(df.index >= DATE_START) & (df.index <= DATE_END)]
        
        df_train = df[df.index < pd.Timestamp(TEST_START)]
        df_test = df[df.index >= pd.Timestamp(TEST_START)]
        
        DATA_CACHE[symbol] = {
            'full': df,
            'train': df_train,
            'test': df_test
        }
        
        print(f"  {symbol}: {len(df)} bars (Train: {len(df_train)}, Test: {len(df_test)})")
        log(f"{symbol}: {len(df)} bars (Train: {len(df_train)}, Test: {len(df_test)})")
    except Exception as e:
        print(f"  [ERROR] {symbol}: {str(e)[:50]}")
        log(f"[ERROR] {symbol}: {str(e)[:50]}")

# ============================================================================
# BACKTEST FUNCTIONS
# ============================================================================

def calculate_metrics(pf, spread_pips):
    total_return = pf.total_return() * 100
    sharpe = pf.sharpe_ratio()
    max_dd = abs(pf.max_drawdown()) * 100
    win_rate = pf.trades.win_rate() * 100 if pf.trades.count() > 0 else 0
    total_trades = pf.trades.count()
    profit_factor = pf.trades.profit_factor() if pf.trades.count() > 0 else 0
    
    return {
        'Total_Return': float(f"{total_return:.2f}"),
        'Max_Drawdown': float(f"{max_dd:.2f}"),
        'Win_Rate': float(f"{win_rate:.2f}"),
        'Total_Trades': int(total_trades),
        'Profit_Factor': float(f"{profit_factor:.2f}"),
        'Sharpe_Ratio': float(f"{sharpe:.3f}")
    }

def backtest_combination(df, entries, tp_pips, sl_pips, spread_pips):
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
        
        return calculate_metrics(pf, spread_pips)
    except Exception as e:
        log(f"[DEBUG] Backtest failed: {str(e)[:100]}")
        return None

# ============================================================================
# INDICATOR TESTING
# ============================================================================

def test_indicator(ind_file):
    ind_name = ind_file.stem
    try:
        ind_num = int(ind_name.split('_')[0])
    except:
        return None
    
    start_time = time.time()
    
    try:
        # Load indicator
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        class_name = None
        for attr in dir(module):
            if attr.startswith('Indicator_'):
                class_name = attr
                break
        
        if not class_name:
            log(f"[ERROR] {ind_name}: No Indicator class found")
            return None
        
        ind_instance = getattr(module, class_name)()
        
        all_combo_results = []
        
        for symbol in SYMBOLS:
            if symbol not in DATA_CACHE:
                continue
            
            spread_pips = SPREADS.get(symbol, 2.0)
            df_train = DATA_CACHE[symbol]['train']
            df_test = DATA_CACHE[symbol]['test']
            df_full = DATA_CACHE[symbol]['full']
            
            best_combo = None
            best_sharpe = -999
            
            for period in PERIOD_VALUES:
                try:
                    # Generate signals ONCE on FULL dataset
                    try:
                        signals_full = ind_instance.generate_signals_fixed(df_full, {'period': period})
                    except:
                        signals_full = ind_instance.generate_signals_fixed(df_full, {})
                    
                    entries_full = signals_full['entries'].values
                    
                    if isinstance(entries_full, np.ndarray):
                        entries_full = pd.Series(entries_full, index=df_full.index)
                    entries_full = entries_full.fillna(False).astype(bool)
                    
                    if entries_full.sum() < 3:
                        continue
                    
                    # Split signals
                    train_mask = df_full.index < pd.Timestamp(TEST_START)
                    test_mask = df_full.index >= pd.Timestamp(TEST_START)
                    
                    entries_train = entries_full[train_mask]
                    entries_test = entries_full[test_mask]
                    
                    # Test all TP/SL combos with CACHED signals
                    for tp, sl in TP_SL_COMBOS:
                        metrics_train = backtest_combination(df_train, entries_train, tp, sl, spread_pips)
                        metrics_test = backtest_combination(df_test, entries_test, tp, sl, spread_pips)
                        metrics_full = backtest_combination(df_full, entries_full, tp, sl, spread_pips)
                        
                        if not metrics_train or not metrics_test or not metrics_full:
                            continue
                        
                        if metrics_train['Sharpe_Ratio'] > best_sharpe:
                            best_sharpe = metrics_train['Sharpe_Ratio']
                            best_combo = {
                                'period': period,
                                'tp_pips': tp,
                                'sl_pips': sl
                            }
                        
                        base_row = {
                            'Indicator_Num': ind_num,
                            'Indicator': ind_name,
                            'Symbol': symbol,
                            'Timeframe': TIMEFRAME,
                            'Period': period,
                            'TP_Pips': tp,
                            'SL_Pips': sl,
                            'Spread_Pips': spread_pips,
                            'Slippage_Pips': SLIPPAGE_PIPS
                        }
                        
                        row_train = base_row.copy()
                        row_train['Phase'] = 'TRAIN'
                        row_train.update(metrics_train)
                        all_combo_results.append(row_train)
                        
                        row_test = base_row.copy()
                        row_test['Phase'] = 'TEST'
                        row_test.update(metrics_test)
                        all_combo_results.append(row_test)
                        
                        row_full = base_row.copy()
                        row_full['Phase'] = 'FULL'
                        row_full.update(metrics_full)
                        all_combo_results.append(row_full)
                
                except Exception as e:
                    log(f"[DEBUG] {ind_name} Period {period}: {str(e)[:100]}")
                    continue
        
        elapsed = time.time() - start_time
        
        if best_combo and len(all_combo_results) > 0:
            full_rows = [r for r in all_combo_results if r['Phase'] == 'FULL']
            if full_rows:
                best_full = max(full_rows, key=lambda x: x['Sharpe_Ratio'])
                msg = f"Ind#{ind_num:03d} | {ind_name[:30]:30s} | {len(SYMBOLS)} symbols | {elapsed:.1f}s | Best: SR={best_full['Sharpe_Ratio']:.2f}, PF={best_full['Profit_Factor']:.2f}, Ret={best_full['Total_Return']:.2f}%, DD={best_full['Max_Drawdown']:.2f}%"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                log(msg)
        else:
            msg = f"Ind#{ind_num:03d} | {ind_name[:30]:30s} | NO RESULTS | {elapsed:.1f}s"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            log(msg)
        
        # Save CSV
        if len(all_combo_results) > 0:
            output_dir = OUTPUT_PATH / "Documentation" / "Fixed_Exit" / TIMEFRAME
            output_file = output_dir / f"{ind_num:03d}_{ind_name}.csv"
            
            df_results = pd.DataFrame(all_combo_results)
            df_results.to_csv(output_file, index=False)
            log(f"[SAVED] {output_file.name}")
        
        return {
            'indicator': ind_name,
            'elapsed': elapsed,
            'results': len(all_combo_results),
            'best_combo': best_combo
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        msg = f"[ERROR] {ind_name}: {str(e)[:100]} ({elapsed:.1f}s)"
        print(msg)
        log(msg)
        return None

# ============================================================================
# RUN TESTS
# ============================================================================

print("\nStarting tests...\n")
log("Starting tests...")

test_start = time.time()

results = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {}
    for ind_name in TEST_INDICATORS:
        ind_file = INDICATORS_PATH / ind_name
        if ind_file.exists():
            futures[executor.submit(test_indicator, ind_file)] = ind_name
    
    for future in as_completed(futures):
        try:
            result = future.result(timeout=INDICATOR_TIMEOUT)
            if result:
                results.append(result)
        except TimeoutError:
            ind_name = futures[future]
            msg = f"[TIMEOUT] {ind_name} exceeded {INDICATOR_TIMEOUT}s"
            print(msg)
            log(msg)
        except Exception as e:
            msg = f"[ERROR] {str(e)[:50]}"
            print(msg)
            log(msg)

test_elapsed = time.time() - test_start

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

log("\n" + "="*80)
log("TEST SUMMARY")
log("="*80)

print(f"Total time: {test_elapsed/60:.2f} minutes")
print(f"Indicators tested: {len(results)}/{len(TEST_INDICATORS)}")
print(f"Average time per indicator: {test_elapsed/len(results):.1f}s" if results else "N/A")

log(f"Total time: {test_elapsed/60:.2f} minutes")
log(f"Indicators tested: {len(results)}/{len(TEST_INDICATORS)}")
log(f"Average time per indicator: {test_elapsed/len(results):.1f}s" if results else "N/A")

if results:
    print("\nResults per indicator:")
    log("\nResults per indicator:")
    for r in results:
        msg = f"  {r['indicator']}: {r['elapsed']:.1f}s, {r['results']} results"
        print(msg)
        log(msg)

print(f"\n✅ Output saved to: {OUTPUT_PATH}")
print(f"✅ Logs saved to: {log_file}")
print("="*80)

log(f"\nOutput: {OUTPUT_PATH}")
log(f"Logs: {log_file}")
log("="*80)
log("QUICK TEST COMPLETE")
log("="*80)
