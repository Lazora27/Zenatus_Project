# -*- coding: utf-8 -*-
"""
PRODUCTION BACKTEST - 1H TIMEFRAME - ADAPTIVE PARAMETERS
=========================================================
Lädt individuell optimierte Parameter pro Indikator
Verwendet genetisch optimierte Configs aus GENETIC_PARAMETER_OPTIMIZER
VectorBT Batch Processing + Signal-Caching
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
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Tier_4_Production"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
SPREADS_PATH = BASE_PATH / "12_Spreads"
CHECKPOINT_PATH = OUTPUT_PATH / "CHECKPOINTS"
CHECKPOINT_PATH.mkdir(parents=True, exist_ok=True)

# PARAMETER CONFIGS (genetisch optimiert)
PARAM_CONFIGS_PATH = OUTPUT_PATH / "Parameter_Configs"

TIMEFRAME = '1h'
FREQ = '1H'
SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
DATE_START = '2020-01-01'
DATE_END = '2025-09-20'
SKIP_INDICATORS = []

# TRADING CONFIG
INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
INDICATOR_TIMEOUT = 300
MAX_WORKERS = 5

# FALLBACK PARAMETERS (wenn keine Config vorhanden)
FALLBACK_PERIODS = [10, 14, 20, 30, 50]
FALLBACK_TP_SL_COMBOS = [(50, 30), (75, 40), (100, 50), (125, 60), (150, 75)]

print("="*80)
print(f"PRODUCTION BACKTEST - ADAPTIVE PARAMETERS - {TIMEFRAME.upper()}")
print("="*80)
print(f"Date: {DATE_START} to {DATE_END}")
print(f"Symbols: {len(SYMBOLS)}")
print(f"Workers: {MAX_WORKERS}")
print(f"Parameter Configs: {PARAM_CONFIGS_PATH}")
print(f"VectorBT Batch Processing: ENABLED")
print("="*80)

# ============================================================================
# LOAD SPREADS & DATA
# ============================================================================

spreads_df = pd.read_csv(SPREADS_PATH / "FTMO_SPREADS_FOREX.csv")
SPREADS = {row['Symbol'].replace('/', '_'): row['Typical_Spread_Pips'] for _, row in spreads_df.iterrows()}
SLIPPAGE_PIPS = 0.5
COMMISSION_PER_LOT = 3.0
pip_value = 0.0001

DATA_CACHE = {}
print("\nLoading data...")
for symbol in SYMBOLS:
    fp = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
    if not fp.exists():
        print(f"[WARN] {symbol} data not found")
        continue
    df = pd.read_csv(fp)
    df.columns = [c.lower() for c in df.columns]
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
    DATA_CACHE[symbol] = {'full': df}
    print(f"  {symbol}: {len(df)} bars")

# ============================================================================
# CHECKPOINT SYSTEM
# ============================================================================

CHECKPOINT_FILE = CHECKPOINT_PATH / f"checkpoint_{TIMEFRAME}_adaptive.json"

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'completed_indicators': []}
    return {'completed_indicators': []}

def save_checkpoint(ind_num):
    checkpoint = load_checkpoint()
    if ind_num not in checkpoint['completed_indicators']:
        checkpoint['completed_indicators'].append(ind_num)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f)

# ============================================================================
# LOAD PARAMETER CONFIG
# ============================================================================

def load_parameter_config(ind_num: int, ind_name: str) -> dict:
    """
    Lädt genetisch optimierte Parameter-Config für Indikator
    Falls nicht vorhanden: Fallback auf Standard-Parameter
    """
    config_file = PARAM_CONFIGS_PATH / f"{ind_num:03d}_{ind_name}_config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"  [CONFIG] Loaded optimized config: {len(config['optimized_periods'])} periods, {len(config['optimized_tp_sl_combos'])} TP/SL combos")
            return config
        except Exception as e:
            print(f"  [WARN] Failed to load config: {str(e)[:50]}")
    
    # Fallback
    print(f"  [FALLBACK] Using default parameters")
    return {
        'optimized_periods': FALLBACK_PERIODS,
        'optimized_tp_sl_combos': FALLBACK_TP_SL_COMBOS,
        'category': 'unknown'
    }

# ============================================================================
# VECTORBT BACKTEST
# ============================================================================

def calculate_metrics(pf, spread_pips):
    trades = pf.trades.count()
    if trades < 3:
        return None
    
    total_return = pf.total_return() * 100
    max_dd = abs(pf.max_drawdown()) * 100
    win_rate = pf.trades.win_rate() * 100
    profit_factor = pf.trades.profit_factor()
    sharpe = pf.sharpe_ratio()
    total_profit = pf.total_profit()
    
    equity = pf.value()
    equity_daily = equity.resample('D').last().dropna()
    
    if len(equity_daily) > 1:
        daily_returns = equity_daily.pct_change().dropna()
        cummax = equity_daily.expanding().max()
        daily_drawdowns = (equity_daily - cummax) / cummax
        max_daily_dd = abs(daily_drawdowns.min()) * 100
        worst_day_loss = abs(daily_returns.min()) * 100 if len(daily_returns) > 0 else 0.0
        daily_dd = max(max_daily_dd, worst_day_loss)
    else:
        daily_dd = max_dd
    
    if np.isnan(profit_factor) or np.isinf(profit_factor):
        profit_factor = 0.0
    if np.isnan(sharpe) or np.isinf(sharpe):
        sharpe = 0.0
    if np.isnan(daily_dd) or np.isinf(daily_dd):
        daily_dd = max_dd
    
    lot_size = POSITION_SIZE / 100000
    total_commission = trades * COMMISSION_PER_LOT * lot_size
    net_profit = total_profit - total_commission
    net_return = (net_profit / INITIAL_CAPITAL) * 100
    
    return {
        'Total_Return': float(f"{net_return:.4f}"),
        'Max_Drawdown': float(f"{max_dd:.4f}"),
        'Daily_Drawdown': float(f"{daily_dd:.4f}"),
        'Win_Rate_%': float(f"{win_rate:.2f}"),
        'Total_Trades': int(trades),
        'Winning_Trades': int(pf.trades.winning.count()),
        'Losing_Trades': int(pf.trades.losing.count()),
        'Gross_Profit': float(f"{total_profit:.2f}"),
        'Commission': float(f"{total_commission:.2f}"),
        'Net_Profit': float(f"{net_profit:.2f}"),
        'Profit_Factor': float(f"{profit_factor:.3f}"),
        'Sharpe_Ratio': float(f"{sharpe:.3f}")
    }

def backtest_batch_combinations(df, entries, tp_sl_combos, spread_pips):
    """VectorBT Batch-Processing: Alle TP/SL Combos auf einmal"""
    try:
        tp_array = []
        sl_array = []
        valid_combos = []
        
        for tp_pips, sl_pips in tp_sl_combos:
            effective_tp = (tp_pips - spread_pips - SLIPPAGE_PIPS) * pip_value
            effective_sl = (sl_pips + spread_pips + SLIPPAGE_PIPS) * pip_value
            
            if effective_tp > 0 and effective_sl > 0:
                tp_array.append(effective_tp)
                sl_array.append(effective_sl)
                valid_combos.append((tp_pips, sl_pips))
        
        if not valid_combos:
            return []
        
        pf = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries,
            exits=False,
            tp_stop=tp_array,
            sl_stop=sl_array,
            init_cash=INITIAL_CAPITAL,
            size=POSITION_SIZE,
            size_type='amount',
            fees=0.0,
            freq=FREQ
        )
        
        results = []
        for idx, (tp_pips, sl_pips) in enumerate(valid_combos):
            try:
                pf_single = pf[idx] if len(valid_combos) > 1 else pf
                metrics = calculate_metrics(pf_single, spread_pips)
                if metrics:
                    metrics['TP_Pips'] = tp_pips
                    metrics['SL_Pips'] = sl_pips
                    results.append(metrics)
            except:
                continue
        
        return results
    except:
        return []

# ============================================================================
# MAIN TESTING FUNCTION
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
        
        indicator_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and (attr_name.startswith('Indicator_') or attr_name.endswith('Indicator')):
                indicator_class = attr
                break
        
        if not indicator_class:
            return None
        
        ind_instance = indicator_class()
        
        # ADAPTIVE: Load optimized parameter config
        param_config = load_parameter_config(ind_num, ind_name)
        period_values = param_config['optimized_periods']
        tp_sl_combos = param_config['optimized_tp_sl_combos']
        
        all_combo_results = []
        
        for symbol in SYMBOLS:
            if symbol not in DATA_CACHE:
                continue
            
            spread_pips = SPREADS.get(symbol, 2.0)
            df_full = DATA_CACHE[symbol]['full']
            
            best_combo = None
            best_sharpe = -999
            
            # Test each optimized period
            for period in period_values:
                try:
                    # Validate period
                    if hasattr(ind_instance, 'PARAMETERS'):
                        params = ind_instance.PARAMETERS
                        if 'period' in params:
                            max_period = params['period'].get('max', 200)
                            if period > max_period:
                                continue
                    
                    # Generate signals
                    try:
                        signals_full = ind_instance.generate_signals_fixed(df_full, {'period': period})
                    except TypeError:
                        try:
                            signals_full = ind_instance.generate_signals_fixed(df_full, {'period': period, 'vfactor': 0.7})
                        except:
                            signals_full = ind_instance.generate_signals_fixed(df_full, {})
                    
                    entries_full = signals_full['entries'].values
                    
                    if isinstance(entries_full, np.ndarray):
                        entries_full = pd.Series(entries_full, index=df_full.index)
                    entries_full = entries_full.fillna(False).astype(bool)
                    
                    if entries_full.sum() < 3:
                        continue
                    
                    # BATCH BACKTEST: All TP/SL combos at once
                    batch_results = backtest_batch_combinations(df_full, entries_full, tp_sl_combos, spread_pips)
                    
                    if not batch_results:
                        continue
                    
                    for metrics_full in batch_results:
                        if metrics_full['Sharpe_Ratio'] > best_sharpe:
                            best_sharpe = metrics_full['Sharpe_Ratio']
                            best_combo = {
                                'period': period,
                                'tp_pips': metrics_full['TP_Pips'],
                                'sl_pips': metrics_full['SL_Pips']
                            }
                        
                        row_full = {
                            'Indicator_Num': ind_num,
                            'Indicator': ind_name,
                            'Symbol': symbol,
                            'Timeframe': TIMEFRAME,
                            'Period': period,
                            'TP_Pips': metrics_full['TP_Pips'],
                            'SL_Pips': metrics_full['SL_Pips'],
                            'Spread_Pips': spread_pips,
                            'Slippage_Pips': SLIPPAGE_PIPS,
                            'Phase': 'FULL'
                        }
                        for key in ['Total_Return', 'Max_Drawdown', 'Daily_Drawdown', 'Win_Rate_%', 
                                   'Total_Trades', 'Winning_Trades', 'Losing_Trades', 'Gross_Profit', 
                                   'Commission', 'Net_Profit', 'Profit_Factor', 'Sharpe_Ratio']:
                            if key in metrics_full:
                                row_full[key] = metrics_full[key]
                        
                        all_combo_results.append(row_full)
                
                except Exception as e:
                    continue
        
        elapsed = time.time() - start_time
        
        if best_combo and len(all_combo_results) > 0:
            full_rows = [r for r in all_combo_results if r['Phase'] == 'FULL']
            if full_rows:
                best_full = max(full_rows, key=lambda x: x['Sharpe_Ratio'])
                total_combos = len(SYMBOLS) * len(period_values) * len(tp_sl_combos)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Ind#{ind_num:03d} | {ind_name:30s} | {len(SYMBOLS)} symbols | {total_combos} combos | {elapsed:.1f}s | Best: SR={best_full['Sharpe_Ratio']:.2f}, PF={best_full['Profit_Factor']:.2f}, Ret={best_full['Total_Return']:.2f}%, DD={best_full['Max_Drawdown']:.2f}%")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ind#{ind_num:03d} | {ind_name[:30]:30s} | NO RESULTS | {elapsed:.1f}s")
        
        if len(all_combo_results) > 0:
            output_dir = OUTPUT_PATH / "Documentation" / "Fixed_Exit" / TIMEFRAME
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{ind_num:03d}_{ind_name}.csv"
            
            df_results = pd.DataFrame(all_combo_results)
            df_results.to_csv(output_file, index=False, float_format='%.6f')
        
        save_checkpoint(ind_num)
        
        return (ind_num, len(all_combo_results))
        
    except Exception as e:
        print(f"\n[ERROR] Ind#{ind_num:03d} | {ind_name} | {str(e)[:50]}")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_file = OUTPUT_PATH / "LOGS" / f"{TIMEFRAME}_ADAPTIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

log("="*80)
log(f"ADAPTIVE PARAMETER BACKTEST START - {TIMEFRAME}")
log("="*80)

all_indicators = sorted(INDICATORS_PATH.glob("*.py"))
checkpoint = load_checkpoint()
completed = checkpoint['completed_indicators']

remaining_indicators = [ind for ind in all_indicators 
                       if int(ind.stem.split('_')[0]) not in completed 
                       and int(ind.stem.split('_')[0]) not in SKIP_INDICATORS]

print(f"\nTotal indicators: {len(all_indicators)}")
print(f"Completed: {len(completed)}")
print(f"Remaining: {len(remaining_indicators)}")
print("\nStarting adaptive backtest...\n")

start_time = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(test_indicator, ind_file): ind_file for ind_file in remaining_indicators}
    
    for future in as_completed(futures):
        try:
            result = future.result(timeout=INDICATOR_TIMEOUT)
        except TimeoutError:
            ind_file = futures[future]
            print(f"\n[TIMEOUT] {ind_file.stem} exceeded {INDICATOR_TIMEOUT}s")
        except Exception as e:
            print(f"\n[ERROR] {str(e)[:50]}")

elapsed = time.time() - start_time

log(f"\nBACKTEST COMPLETE!")
log(f"Total time: {elapsed/3600:.2f}h")

print(f"\n{'='*80}")
print(f"COMPLETE! Results in: Documentation/Fixed_Exit/{TIMEFRAME}/")
print(f"{'='*80}")
