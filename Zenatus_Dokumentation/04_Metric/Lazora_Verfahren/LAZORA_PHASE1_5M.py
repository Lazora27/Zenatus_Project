# -*- coding: utf-8 -*-
"""
LAZORA PHASE 1 - PRODUCTION BACKTEST 1H
========================================
Sobol Sequence Sampling + Walk-Forward 80/20 + vectorbt
Features:
- Intelligent Parameter Sampling (500 combos via Sobol)
- Walk-Forward 80/20 Split
- Checkpoint System
- Live Progress Output
- Heatmap Data Generation
"""

import sys
from pathlib import Path
import time
import pandas as pd
import numpy as np
import importlib.util
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed, TimeoutError
import multiprocessing
from datetime import datetime
import json
from scipy.stats import qmc
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

BASE_PATH = Path(r"D:\2_Trading\Superindikator_Alpha")
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Production_595_Ultimate"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System"
SPREADS_PATH = BASE_PATH / "12_Spreads"
LAZORA_PATH = BASE_PATH / "08_Lazora_Verfahren"
HEATMAP_PATH = BASE_PATH / "08_Heatmaps" / "Fixed_Exit"
CHECKPOINT_PATH = OUTPUT_PATH / "CHECKPOINTS"
CHECKPOINT_PATH.mkdir(parents=True, exist_ok=True)

TIMEFRAME = '5m'
FREQ = '5T'
SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD']
DATE_START = '2020-07-01'  # After COVID crash!
DATE_END = '2025-09-20'    # Real data end
SKIP_INDICATORS = [8]

# Walk-Forward 80/20
TRAIN_END = '2024-07-01'   # 4 years TRAIN (Jul 2020 - Jul 2024)
TEST_START = '2024-07-01'  # 1 year TEST (Jul 2024 - Sep 2025)

# Trading Config
INITIAL_CAPITAL = 10000
LEVERAGE = 10
POSITION_SIZE = 100
INDICATOR_TIMEOUT = 300  # 5min for 1H
MAX_WORKERS_SYMBOLS = min(12, multiprocessing.cpu_count())  # Use all available cores!

# Lazora Phase 1 Config
PHASE1_SAMPLES = 100  # Sobol samples (REDUCED FOR SPEED! Pragmatic for slow indicators)

print("="*80)
print(f"LAZORA PHASE 1 - {TIMEFRAME.upper()}")
print("="*80)
print(f"Method: Sobol Sequence Sampling")
print(f"Samples: {PHASE1_SAMPLES}")
print(f"Date: {DATE_START} to {DATE_END}")
print(f"Train: {DATE_START} to {TRAIN_END} (80%)")
print(f"Test:  {TEST_START} to {DATE_END} (20%)")
print(f"Symbols: {len(SYMBOLS)}")
print("="*80)

# Load Matrix Ranges (INTELLIGENT VERSION!)
PARAM_PATH = BASE_PATH / "01_Backtest_System" / "Parameter_Optimization"
matrix_file = LAZORA_PATH / "PARAMETER_HANDBOOK_INTELLIGENT.json"
if not matrix_file.exists():
    print("[WARNING] Intelligent handbook not found, using standard...")
    matrix_file = PARAM_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"

with open(matrix_file, 'r', encoding='utf-8') as f:
    handbook = json.load(f)
    MATRIX_DATA = {}
    for ind in handbook:
        ind_num = ind['Indicator_Num']
        # Build matrix info from handbook
        entry_matrix = {}
        for param_name, param_config in ind['Entry_Params'].items():
            entry_matrix[param_name] = {
                'min': min(param_config['values']),
                'max': max(param_config['values']),
                'steps': len(param_config['values']),
                'type': param_config.get('type', 'int'),
                'default': param_config.get('default', param_config['values'][len(param_config['values'])//2]),
                'values': param_config['values']
            }
        
        MATRIX_DATA[ind_num] = {
            'Indicator_Num': ind_num,
            'Indicator_Name': ind['Indicator_Name'],
            'Entry_Matrix': entry_matrix,
            'Exit_Matrix': {},  # Will be filled from TP/SL
            'Dimensionality': len(entry_matrix)
        }

# Load Spreads
spreads_df = pd.read_csv(SPREADS_PATH / "FTMO_SPREADS_FOREX.csv")
SPREADS = {row['Symbol'].replace('/', '_'): row['Typical_Spread_Pips'] for _, row in spreads_df.iterrows()}
SLIPPAGE_PIPS = 0.5
COMMISSION_PER_LOT = 3.0
pip_value = 0.0001

# TP/SL from old system
TP_VALUES = [20, 30, 40, 50, 60, 75, 100, 125, 150, 175, 200, 250, 300]
SL_VALUES = [10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150]

# Load Data
DATA_CACHE = {}
print("\nLoading data...")
for symbol in SYMBOLS:
    fp = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
    if not fp.exists():
        continue
    df = pd.read_csv(fp)
    df.columns = [c.lower() for c in df.columns]
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
    
    df_train = df[(df.index >= DATE_START) & (df.index < TRAIN_END)]
    df_test = df[(df.index >= TEST_START) & (df.index < DATE_END)]
    
    DATA_CACHE[symbol] = {
        'full': df,
        'train': df_train,
        'test': df_test
    }
    print(f"  {symbol}: {len(df)} bars (Train: {len(df_train)}, Test: {len(df_test)})")

# ============================================================================
# CHECKPOINT SYSTEM
# ============================================================================

CHECKPOINT_FILE = CHECKPOINT_PATH / f"lazora_phase1_{TIMEFRAME}.json"

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
# SOBOL SAMPLING
# ============================================================================

def generate_sobol_samples(ind_num, n_samples=500):
    """
    Generate Sobol Sequence samples for indicator parameters
    Uses INTELLIGENT RANGES from handbook!
    Returns: List of parameter combinations
    """
    if ind_num not in MATRIX_DATA:
        return []
    
    matrix = MATRIX_DATA[ind_num]
    entry_params = matrix['Entry_Matrix']
    
    if len(entry_params) == 0:
        # No entry parameters, only TP/SL
        combos = []
        for tp in TP_VALUES:
            for sl in SL_VALUES:
                if tp > sl * 1.5:
                    combos.append({'tp_pips': tp, 'sl_pips': sl})
        return combos[:n_samples]
    
    # Generate Sobol samples for Entry parameters
    n_dims = len(entry_params)
    sobol = qmc.Sobol(d=n_dims, scramble=True, seed=42)
    sobol_points = sobol.random(n_samples)
    
    param_names = list(entry_params.keys())
    entry_combos = []
    
    for point in sobol_points:
        params = {}
        for i, param_name in enumerate(param_names):
            param_config = entry_params[param_name]
            param_values = param_config.get('values', [])
            
            if len(param_values) > 0:
                # Use intelligent discrete values!
                idx = int(point[i] * (len(param_values) - 1))
                value = param_values[idx]
            else:
                # Fallback to continuous range
                min_val = param_config['min']
                max_val = param_config['max']
                param_type = param_config['type']
                
                value = min_val + point[i] * (max_val - min_val)
                
                if param_type == 'int':
                    value = int(round(value))
                elif param_type == 'float':
                    value = round(value, 4)
            
            params[param_name] = value
        
        entry_combos.append(params)
    
    # Combine Entry params with TP/SL (sample TP/SL uniformly)
    import random
    random.seed(42)
    
    all_combos = []
    tp_sl_pairs = [(tp, sl) for tp in TP_VALUES for sl in SL_VALUES if tp > sl * 1.5]
    
    for entry_param in entry_combos:
        # Pick random TP/SL for this entry combo
        tp, sl = random.choice(tp_sl_pairs)
        combo = entry_param.copy()
        combo['tp_pips'] = tp
        combo['sl_pips'] = sl
        all_combos.append(combo)
    
    return all_combos

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
    
    # ===================================================================
    # CORRECT DAILY DRAWDOWN (PROP FIRM STYLE!)
    # ===================================================================
    equity = pf.value()
    
    # Resample to daily (last value of each day)
    equity_daily = equity.resample('D').last().dropna()
    
    if len(equity_daily) > 1:
        # Calculate daily returns (for worst day)
        daily_returns = equity_daily.pct_change().dropna()
        worst_day_loss = abs(daily_returns.min()) * 100 if len(daily_returns) > 0 else 0.0
        
        # OPTIMIZED: Calculate max drawdown WITHIN each day (FAST!)
        # Group by day ONCE (not in loop!)
        equity_grouped = equity.groupby(pd.Grouper(freq='D'))
        
        daily_dds = []
        for date, day_equity in equity_grouped:
            if len(day_equity) > 0:
                day_peak = day_equity.expanding().max()
                day_dd = ((day_equity - day_peak) / day_peak).min()
                daily_dds.append(abs(day_dd) * 100)
        
        # Daily DD = max of: worst intraday DD OR worst day-to-day loss
        max_intraday_dd = max(daily_dds) if daily_dds else 0.0
        daily_dd = max(max_intraday_dd, worst_day_loss)
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
        'Profit_Factor': float(f"{profit_factor:.3f}"),
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
        # Silent fail - return None (expected for some combos)
        return None

# ============================================================================
# SYMBOL TESTING FUNCTION (for parallel execution)
# ============================================================================

def test_symbol_for_indicator(symbol, ind_instance, ind_num, ind_name, sobol_combos):
    """Test all Sobol combinations for ONE symbol - VECTORIZED!"""
    
    if symbol not in DATA_CACHE:
        return None
    
    spread_pips = SPREADS.get(symbol, 2.0)
    df_train = DATA_CACHE[symbol]['train']
    df_test = DATA_CACHE[symbol]['test']
    df_full = DATA_CACHE[symbol]['full']
    
    symbol_results = []
    symbol_heatmap = []
    
    # ===================================================================
    # PROFILING: Track time for each phase
    # ===================================================================
    time_precompute = 0.0
    time_train_pf = 0.0
    time_daily_dd = 0.0
    time_test_full = 0.0
    
    # ===================================================================
    # OPTIMIZATION: PRE-COMPUTE INDICATOR VALUES FOR ALL UNIQUE PARAMS
    # ===================================================================
    
    t0_precompute = time.time()
    
    n_combos = len(sobol_combos)
    n_bars = len(df_train)
    
    # Extract unique parameter combinations (excluding TP/SL)
    unique_params = {}
    param_to_combos = {}  # Map param_key -> list of combo indices
    
    for combo_idx, combo in enumerate(sobol_combos):
        entry_params = {k: v for k, v in combo.items() if k not in ['tp_pips', 'sl_pips']}
        param_key = tuple(sorted(entry_params.items()))
        
        if param_key not in unique_params:
            unique_params[param_key] = entry_params
            param_to_combos[param_key] = []
        param_to_combos[param_key].append(combo_idx)
    
    print(f"  [{symbol}] Pre-computing signals for {len(unique_params)} unique param sets (from {n_combos} combos)...", flush=True)
    
    # Pre-compute signals for all unique parameter sets
    precomputed_signals = {}
    computed_count = 0
    last_print_time = time.time()
    
    for param_key, entry_params in unique_params.items():
        try:
            signals = ind_instance.generate_signals_fixed(df_train, entry_params)
            entries = signals['entries'].values
            
            if isinstance(entries, np.ndarray):
                entries = pd.Series(entries, index=df_train.index)
            entries = entries.fillna(False).astype(bool)
            
            if entries.sum() >= 3:
                precomputed_signals[param_key] = entries.values
            
            computed_count += 1
            # Print only every 5 seconds (not every 50 combos!)
            if time.time() - last_print_time > 5.0:
                print(f"  [{symbol}] {computed_count}/{len(unique_params)} param sets computed...", flush=True)
                last_print_time = time.time()
        except:
            continue
    
    print(f"  [{symbol}] Pre-computation done! {len(precomputed_signals)} valid param sets. Building matrix...", flush=True)
    
    time_precompute = time.time() - t0_precompute
    
    # ===================================================================
    # VECTORIZED BACKTEST - ALL COMBOS AT ONCE!
    # ===================================================================
    
    t0_train_pf = time.time()
    
    # Build entry matrix: (n_bars, n_combos)
    entries_matrix = np.zeros((n_bars, n_combos), dtype=bool)
    tp_array = np.zeros(n_combos, dtype=float)
    sl_array = np.zeros(n_combos, dtype=float)
    
    valid_combos = []
    for combo_idx, combo in enumerate(sobol_combos):
        tp_pips = combo['tp_pips']
        sl_pips = combo['sl_pips']
        entry_params = {k: v for k, v in combo.items() if k not in ['tp_pips', 'sl_pips']}
        param_key = tuple(sorted(entry_params.items()))
        
        # Use pre-computed signals!
        if param_key not in precomputed_signals:
            continue
        
        try:
            entries = precomputed_signals[param_key]
            
            # Store in matrix (already validated during pre-compute)
            entries_matrix[:, combo_idx] = entries
            
            # Calculate effective TP/SL
            effective_tp = (tp_pips - spread_pips - SLIPPAGE_PIPS) * pip_value
            effective_sl = (sl_pips + spread_pips + SLIPPAGE_PIPS) * pip_value
            
            if effective_tp <= 0 or effective_sl <= 0:
                continue
            
            tp_array[combo_idx] = effective_tp
            sl_array[combo_idx] = effective_sl
            valid_combos.append(combo_idx)
        
        except:
            continue
    
    if len(valid_combos) == 0:
        print(f"  [{symbol}] No valid combos!", flush=True)
        return {'symbol': symbol, 'results': [], 'heatmap': [], 'best_combo': None}
    
    # Keep only valid combos
    entries_matrix = entries_matrix[:, valid_combos]
    tp_array = tp_array[valid_combos]
    sl_array = sl_array[valid_combos]
    
    print(f"  [{symbol}] Backtesting {len(valid_combos)} combos VECTORIZED...", flush=True)
    
    # ===================================================================
    # SINGLE VECTORIZED BACKTEST FOR ALL COMBOS!
    # ===================================================================
    
    try:
        pf = vbt.Portfolio.from_signals(
            close=df_train['close'],
            entries=entries_matrix,
            exits=False,
            tp_stop=tp_array,
            sl_stop=sl_array,
            init_cash=INITIAL_CAPITAL,
            size=POSITION_SIZE,
            size_type='amount',
            fees=0.0,
            freq=FREQ,
            group_by=False  # Each combo separate
        )
        
        # Extract metrics for ALL combos at once
        total_returns = pf.total_return() * 100
        max_dds = abs(pf.max_drawdown()) * 100
        sharpes = pf.sharpe_ratio()
        profit_factors = pf.trades.profit_factor()
        win_rates = pf.trades.win_rate() * 100
        total_trades = pf.trades.count()
        
        # Find best combo (by Sharpe on TRAIN)
        best_idx = np.nanargmax(sharpes.values if hasattr(sharpes, 'values') else sharpes)
        best_combo_idx = valid_combos[best_idx]
        best_combo_dict = sobol_combos[best_combo_idx]
        
        print(f"  [{symbol}] DONE! Best Combo #{best_combo_idx}: SR={sharpes.iloc[best_idx]:.2f}", flush=True)
        
        time_train_pf = time.time() - t0_train_pf
        
        # ===================================================================
        # NOW TEST ONLY TOP 20 COMBOS ON TEST + FULL
        # ===================================================================
        
        # Get top 20 by Sharpe
        top_n = min(20, len(valid_combos))
        top_indices = np.argsort(sharpes.values if hasattr(sharpes, 'values') else sharpes)[-top_n:][::-1]
        
        # ===================================================================
        # CALCULATE CORRECT DAILY DD FOR TOP 20 (VECTORIZED, NO pf_single!)
        # ===================================================================
        
        t0_daily_dd = time.time()
        
        # Get equity curves for Top 20 combos
        equity_all = pf.value()  # DataFrame: (bars, combos)
        equity_top = equity_all.iloc[:, top_indices]  # Only Top 20
        
        # Calculate Daily DD per combo (VECTORIZED!)
        daily_dds_per_combo = {}
        
        for col_idx, combo_col in enumerate(equity_top.columns):
            equity_series = equity_top.iloc[:, col_idx]
            
            # Resample to daily
            equity_daily = equity_series.resample('D').last().dropna()
            
            if len(equity_daily) > 1:
                # Day-to-day loss
                daily_returns = equity_daily.pct_change().dropna()
                worst_day_loss = abs(daily_returns.min()) * 100 if len(daily_returns) > 0 else 0.0
                
                # Intraday peak-to-trough (OPTIMIZED!)
                equity_grouped = equity_series.groupby(pd.Grouper(freq='D'))
                daily_dds = []
                for date, day_equity in equity_grouped:
                    if len(day_equity) > 0:
                        day_peak = day_equity.expanding().max()
                        day_dd = ((day_equity - day_peak) / day_peak).min()
                        daily_dds.append(abs(day_dd) * 100)
                
                max_intraday_dd = max(daily_dds) if daily_dds else 0.0
                daily_dd = max(max_intraday_dd, worst_day_loss)
            else:
                daily_dd = abs(pf.max_drawdown().iloc[combo_col]) * 100
            
            daily_dds_per_combo[combo_col] = daily_dd
        
        time_daily_dd = time.time() - t0_daily_dd
        
        print(f"  [{symbol}] Testing TOP {top_n} combos on TEST+FULL...", flush=True)
        
        t0_test_full = time.time()
        
        # ===================================================================
        # OPTIMIZATION: PRE-COMPUTE TEST/FULL SIGNALS FOR TOP COMBOS
        # ===================================================================
        
        # Collect unique param sets for top combos
        top_unique_params = {}
        top_param_to_idx = {}
        
        for rank, idx in enumerate(top_indices):
            combo_idx = valid_combos[idx]
            combo = sobol_combos[combo_idx]
            entry_params = {k: v for k, v in combo.items() if k not in ['tp_pips', 'sl_pips']}
            param_key = tuple(sorted(entry_params.items()))
            
            if param_key not in top_unique_params:
                top_unique_params[param_key] = entry_params
                top_param_to_idx[param_key] = []
            top_param_to_idx[param_key].append((rank, idx, combo_idx, combo))
        
        # Pre-compute TEST and FULL signals for unique param sets
        precomputed_test = {}
        precomputed_full = {}
        
        for param_key, entry_params in top_unique_params.items():
            try:
                signals_test = ind_instance.generate_signals_fixed(df_test, entry_params)
                precomputed_test[param_key] = signals_test['entries'].fillna(False).astype(bool)
                
                signals_full = ind_instance.generate_signals_fixed(df_full, entry_params)
                precomputed_full[param_key] = signals_full['entries'].fillna(False).astype(bool)
            except:
                continue
        
        # Track best combo metrics (CORRECTLY!)
        best_combo_metrics_train = None
        best_combo_metrics_test = None
        best_combo_metrics_full = None
        best_combo_params = best_combo_dict.copy()
        
        # Process top combos using pre-computed signals
        for rank, idx in enumerate(top_indices):
            combo_idx = valid_combos[idx]
            combo = sobol_combos[combo_idx]
            
            tp_pips = combo['tp_pips']
            sl_pips = combo['sl_pips']
            entry_params = {k: v for k, v in combo.items() if k not in ['tp_pips', 'sl_pips']}
            param_key = tuple(sorted(entry_params.items()))
            
            # TRAIN metrics (from ALREADY COMPUTED vectorized backtest!)
            # Extract from pf (already computed for ALL combos)
            # Get the column name from equity_top (which was created with top_indices)
            equity_col_name = equity_top.columns[rank]  # ← CORRECT: Use rank to get column name!
            
            metrics_train = {
                'Total_Return': float(f"{total_returns.iloc[idx]:.4f}"),
                'Max_Drawdown': float(f"{max_dds.iloc[idx]:.4f}"),
                'Daily_Drawdown': float(f"{daily_dds_per_combo[equity_col_name]:.4f}"),  # ← NOW CORRECT!
                'Win_Rate_%': float(f"{win_rates.iloc[idx]:.2f}"),
                'Total_Trades': int(total_trades.iloc[idx]),
                'Profit_Factor': float(f"{profit_factors.iloc[idx]:.3f}"),
                'Sharpe_Ratio': float(f"{sharpes.iloc[idx]:.3f}")
            }
            
            # TEST + FULL (use pre-computed signals!)
            try:
                if param_key not in precomputed_test or param_key not in precomputed_full:
                    continue
                
                entries_test = precomputed_test[param_key]
                metrics_test = backtest_combination(df_test, entries_test, tp_pips, sl_pips, spread_pips)
                
                entries_full = precomputed_full[param_key]
                metrics_full = backtest_combination(df_full, entries_full, tp_pips, sl_pips, spread_pips)
                
                if not metrics_test or not metrics_full:
                    continue
                
                # Store 3 rows
                base_row = {
                    'Indicator_Num': ind_num,
                    'Indicator': ind_name,
                    'Symbol': symbol,
                    'Timeframe': TIMEFRAME,
                    'Combo_Index': combo_idx,
                    'Rank': rank + 1,
                    'TP_Pips': tp_pips,
                    'SL_Pips': sl_pips,
                    'Spread_Pips': spread_pips,
                    'Slippage_Pips': SLIPPAGE_PIPS
                }
                
                for k, v in entry_params.items():
                    base_row[k] = v
                
                row_train = base_row.copy()
                row_train['Phase'] = 'TRAIN'
                row_train.update(metrics_train)
                symbol_results.append(row_train)
                
                row_test = base_row.copy()
                row_test['Phase'] = 'TEST'
                row_test.update(metrics_test)
                symbol_results.append(row_test)
                
                row_full = base_row.copy()
                row_full['Phase'] = 'FULL'
                row_full.update(metrics_full)
                symbol_results.append(row_full)
                
                # Heatmap
                heatmap_row = combo.copy()
                heatmap_row.update({
                    'Symbol': symbol,
                    'Sharpe_Ratio': metrics_train['Sharpe_Ratio'],
                    'Profit_Factor': metrics_train['Profit_Factor'],
                    'Total_Return': metrics_train['Total_Return'],
                    'Max_Drawdown': metrics_train['Max_Drawdown']
                })
                symbol_heatmap.append(heatmap_row)
                
                # Track best combo (rank 0 = best by Sharpe)
                if rank == 0:
                    best_combo_metrics_train = metrics_train.copy()
                    best_combo_metrics_test = metrics_test.copy() if metrics_test else None
                    best_combo_metrics_full = metrics_full.copy() if metrics_full else None
            
            except Exception as e:
                # Log error but continue with other combos
                continue
        
        # Check if we have any valid results
        if len(symbol_results) == 0:
            print(f"  [{symbol}] ⚠️  No valid TEST/FULL results for top combos!", flush=True)
            return {'symbol': symbol, 'results': [], 'heatmap': [], 'best_combo': None}
        
        # Best combo for global tracking (CORRECT!)
        best_combo_obj = {
            'params': best_combo_params,
            'metrics_train': best_combo_metrics_train,
            'metrics_test': best_combo_metrics_test,
            'metrics_full': best_combo_metrics_full
        }
        
        time_test_full = time.time() - t0_test_full
        
        # ===================================================================
        # PROFILING OUTPUT
        # ===================================================================
        total_time = time_precompute + time_train_pf + time_daily_dd + time_test_full
        print(f"  [{symbol}] ⏱️  pre={time_precompute:.1f}s | train_pf={time_train_pf:.1f}s | daily_dd={time_daily_dd:.1f}s | test_full={time_test_full:.1f}s | total={total_time:.1f}s", flush=True)
        print(f"  [{symbol}] ✅ COMPLETE! Documented {len(symbol_results)//3} top combos", flush=True)
        
        return {
            'symbol': symbol,
            'results': symbol_results,
            'heatmap': symbol_heatmap,
            'best_combo': best_combo_obj
        }
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"  [{symbol}] ❌ ERROR: {error_msg}", flush=True)
        if len(error_msg) > 100:
            # Print full traceback for debugging
            print(f"  [{symbol}] Full traceback:", flush=True)
            traceback.print_exc()
        return {'symbol': symbol, 'results': [], 'heatmap': [], 'best_combo': None}

# ============================================================================
# MAIN TESTING FUNCTION
# ============================================================================

def test_indicator(ind_file):
    ind_name = ind_file.stem
    try:
        ind_num = int(ind_name.split('_')[0])
    except:
        return None
    
    checkpoint = load_checkpoint()
    if ind_num in checkpoint['completed_indicators']:
        print(f"[SKIP] Indicator {ind_num:03d} already completed")
        return None
    
    if ind_num in SKIP_INDICATORS:
        return None
    
    start_time = time.time()
    
    print(f"\n[START] Ind#{ind_num:03d} | {ind_name} | Loading indicator class...")
    
    try:
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        print(f"[LOAD] Ind#{ind_num:03d} | Module loaded, searching for class...")
        
        # Try multiple class name patterns
        class_name = None
        
        # Pattern 1: Exact match with filename
        for attr in dir(module):
            if attr.lower() == ind_name.lower():
                class_name = attr
                break
        
        # Pattern 2: Look for "Indicator_*" classes
        if not class_name:
            for attr in dir(module):
                if attr.startswith('Indicator_') and not attr.startswith('_'):
                    class_name = attr
                    break
        
        # Pattern 3: Look for any class that contains indicator number
        if not class_name:
            ind_num_str = f"{ind_num:03d}"
            for attr in dir(module):
                if ind_num_str in attr and attr[0].isupper():
                    class_name = attr
                    break
        
        if not class_name:
            print(f"[ERROR] Ind#{ind_num:03d} | Class not found! Available: {[a for a in dir(module) if not a.startswith('_')][:5]}")
            return None
        
        ind_instance = getattr(module, class_name)()
        print(f"[LOAD] Ind#{ind_num:03d} | Class instantiated, generating Sobol samples...")
        
        # Generate Sobol samples
        sobol_combos = generate_sobol_samples(ind_num, PHASE1_SAMPLES)
        print(f"[SOBOL] Ind#{ind_num:03d} | Generated {len(sobol_combos)} combinations")
        
        if len(sobol_combos) == 0:
            print(f"[SKIP] Ind#{ind_num:03d} | No valid combinations")
            return None
        
        # Store ALL combination results for CSV and Heatmap
        all_combo_results = []
        heatmap_data = []
        best_combo_global = None
        best_sharpe_global = -999
        
        print(f"[PARALLEL] Ind#{ind_num:03d} | Starting 6 parallel symbol tests...")
        
        # ===================================================================
        # PARALLEL SYMBOL TESTING (6 Symbols gleichzeitig!)
        # ===================================================================
        
        # Keep ThreadPool (ProcessPool has pickling issues with indicator instances)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_SYMBOLS) as executor:
            futures = {
                executor.submit(test_symbol_for_indicator, symbol, ind_instance, ind_num, ind_name, sobol_combos): symbol
                for symbol in SYMBOLS
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=600)  # 600s (10min) per symbol max
                    
                    if result and result['results']:
                        all_combo_results.extend(result['results'])
                        heatmap_data.extend(result['heatmap'])
                        
                        # Track global best
                        if result['best_combo']:
                            combo_sharpe = result['best_combo']['metrics_full']['Sharpe_Ratio']
                            if combo_sharpe > best_sharpe_global:
                                best_sharpe_global = combo_sharpe
                                best_combo_global = result['best_combo']
                
                except TimeoutError:
                    symbol = futures[future]
                    print(f"\n[TIMEOUT] Ind#{ind_num:03d} | {symbol} exceeded 600s (10min)")
                except Exception as e:
                    symbol = futures[future]
                    print(f"\n[ERROR] Ind#{ind_num:03d} | {symbol}: {str(e)[:50]}")
        
        # ===================================================================
        # END PARALLEL SECTION
        # ===================================================================
        
        elapsed = time.time() - start_time
        
        # Print terminal output
        if best_combo_global:
            m = best_combo_global['metrics_full']
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ind#{ind_num:03d} | {ind_name[:30]:30s} | {len(SYMBOLS)} symbols | {elapsed:.1f}s | Best: SR={m['Sharpe_Ratio']:.2f}, PF={m['Profit_Factor']:.2f}, Ret={m['Total_Return']:.2f}%, DD={m['Max_Drawdown']:.2f}%")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ind#{ind_num:03d} | {ind_name[:30]:30s} | NO RESULTS | {elapsed:.1f}s")
        
        # Save CSV documentation
        if len(all_combo_results) > 0:
            output_dir = OUTPUT_PATH / "Documentation" / "Fixed_Exit" / TIMEFRAME
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{ind_num:03d}_{ind_name}.csv"
            
            df_results = pd.DataFrame(all_combo_results)
            df_results.to_csv(output_file, index=False, float_format='%.6f')
        
        # Save Heatmap data
        if len(heatmap_data) > 0:
            heatmap_dir = HEATMAP_PATH / TIMEFRAME
            heatmap_file = heatmap_dir / f"{ind_num:03d}_{ind_name}_heatmap_data.csv"
            
            df_heatmap = pd.DataFrame(heatmap_data)
            df_heatmap.to_csv(heatmap_file, index=False, float_format='%.6f')
        
        # Save checkpoint
        save_checkpoint(ind_num)
        
        return len(all_combo_results)
        
    except Exception as e:
        print(f"\n[ERROR] Ind#{ind_num:03d} | {ind_name} | {str(e)[:50]}")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_file = OUTPUT_PATH / "LOGS" / f"LAZORA_PHASE1_{TIMEFRAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

log("="*80)
log(f"LAZORA PHASE 1 START - {TIMEFRAME}")
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
print("\nStarting Lazora Phase 1...\n")

start_time = time.time()

# Sequential processing of indicators (one at a time, but symbols parallel within each)
for ind_file in remaining_indicators:
    try:
        result = test_indicator(ind_file)
    except Exception as e:
        print(f"\n[ERROR] {ind_file.stem}: {str(e)[:50]}")

elapsed = time.time() - start_time

log(f"\nLAZORA PHASE 1 COMPLETE!")
log(f"Total time: {elapsed/3600:.2f}h")

print(f"\n{'='*80}")
print(f"LAZORA PHASE 1 COMPLETE!")
print(f"CSV Results: Documentation/Fixed_Exit/{TIMEFRAME}/")
print(f"Heatmap Data: 08_Heatmaps/Fixed_Exit/{TIMEFRAME}/")
print(f"{'='*80}")
