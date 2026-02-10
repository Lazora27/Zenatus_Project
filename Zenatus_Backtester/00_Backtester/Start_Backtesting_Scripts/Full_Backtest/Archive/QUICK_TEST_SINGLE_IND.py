"""
QUICK TEST - Single Indicator
Test ob Signal-Caching + Single-Calls funktionieren
"""

import sys
from pathlib import Path
import time
import pandas as pd
import numpy as np
import importlib.util
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    import vectorbt as vbt
except:
    print("[FATAL] vectorbt not installed!")
    sys.exit(1)

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Production_595_Ultimate"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"

sys.path.insert(0, str(INDICATORS_PATH))

TIMEFRAME = '1h'
SYMBOL = 'EUR_USD'
DATE_START = '2020-01-01'
DATE_END = '2025-09-20'
TEST_START = '2024-06-01'

INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
SLIPPAGE_PIPS = 1.0
SPREAD_PIPS = 1.8
pip_value = 0.0001
FREQ = '1h'

TP_SL_COMBOS = [(50, 25), (100, 50), (150, 75)]  # Nur 3 Combos zum Testen

print("="*80)
print("QUICK TEST - Single Indicator")
print("="*80)

# Load data
print(f"\nLoading {SYMBOL} data...")
df = pd.read_csv(DATA_PATH / TIMEFRAME / SYMBOL / f"{SYMBOL}_aggregated.csv")
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)
df = df[(df.index >= DATE_START) & (df.index <= DATE_END)]

df_train = df[df.index < pd.Timestamp(TEST_START)]
df_test = df[df.index >= pd.Timestamp(TEST_START)]

print(f"  Total: {len(df)} bars")
print(f"  Train: {len(df_train)} bars")
print(f"  Test: {len(df_test)} bars")

# Load indicator
ind_file = INDICATORS_PATH / "001_trend_sma.py"
print(f"\nLoading indicator: {ind_file.name}")

spec = importlib.util.spec_from_file_location("001_trend_sma", ind_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class_name = None
for attr in dir(module):
    if attr.startswith('Indicator_'):
        class_name = attr
        break

if not class_name:
    print("[ERROR] No Indicator class found!")
    sys.exit(1)

ind_instance = getattr(module, class_name)()
print(f"  Class: {class_name}")

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
        print(f"[ERROR] Backtest failed: {str(e)[:100]}")
        return None

# Test Signal-Caching
print("\n" + "="*80)
print("TESTING SIGNAL-CACHING")
print("="*80)

period = 20
print(f"\nGenerating signals for period={period}...")
start = time.time()

try:
    signals_full = ind_instance.generate_signals_fixed(df, {'period': period})
except Exception as e:
    print(f"[ERROR] Signal generation failed: {e}")
    try:
        signals_full = ind_instance.generate_signals_fixed(df, {})
    except Exception as e2:
        print(f"[ERROR] Fallback also failed: {e2}")
        sys.exit(1)

entries_full = signals_full['entries'].values
if isinstance(entries_full, np.ndarray):
    entries_full = pd.Series(entries_full, index=df.index)
entries_full = entries_full.fillna(False).astype(bool)

signal_time = time.time() - start
print(f"  ✅ Signals generated in {signal_time:.2f}s")
print(f"  Total entries: {entries_full.sum()}")

# Split signals
train_mask = df.index < pd.Timestamp(TEST_START)
test_mask = df.index >= pd.Timestamp(TEST_START)

entries_train = entries_full[train_mask]
entries_test = entries_full[test_mask]

print(f"  Train entries: {entries_train.sum()}")
print(f"  Test entries: {entries_test.sum()}")

# Test backtests with cached signals
print(f"\nTesting {len(TP_SL_COMBOS)} TP/SL combinations...")
results = []

for tp, sl in TP_SL_COMBOS:
    print(f"  Testing TP={tp}, SL={sl}...", end=" ")
    
    metrics_train = backtest_combination(df_train, entries_train, tp, sl, SPREAD_PIPS)
    metrics_test = backtest_combination(df_test, entries_test, tp, sl, SPREAD_PIPS)
    metrics_full = backtest_combination(df, entries_full, tp, sl, SPREAD_PIPS)
    
    if metrics_train and metrics_test and metrics_full:
        print(f"✅ SR={metrics_full['Sharpe_Ratio']:.2f}, PF={metrics_full['Profit_Factor']:.2f}")
        results.append({
            'TP': tp,
            'SL': sl,
            'Train_SR': metrics_train['Sharpe_Ratio'],
            'Test_SR': metrics_test['Sharpe_Ratio'],
            'Full_SR': metrics_full['Sharpe_Ratio']
        })
    else:
        print("❌ FAILED")

total_time = time.time() - start
print(f"\n{'='*80}")
print(f"RESULTS:")
print(f"  Signal generation: {signal_time:.2f}s (1x)")
print(f"  Backtests: {total_time - signal_time:.2f}s ({len(TP_SL_COMBOS)*3} runs)")
print(f"  Total time: {total_time:.2f}s")
print(f"  Successful combos: {len(results)}/{len(TP_SL_COMBOS)}")
print(f"{'='*80}")

if len(results) > 0:
    print("\n✅ TEST PASSED! Signal-Caching funktioniert!")
    print("\nBest combo:")
    best = max(results, key=lambda x: x['Full_SR'])
    print(f"  TP={best['TP']}, SL={best['SL']}")
    print(f"  Train SR: {best['Train_SR']:.3f}")
    print(f"  Test SR: {best['Test_SR']:.3f}")
    print(f"  Full SR: {best['Full_SR']:.3f}")
else:
    print("\n❌ TEST FAILED! Keine Results!")
