# -*- coding: utf-8 -*-
"""
DEBUG: Test vectorbt metric calculations
"""

import sys
import pandas as pd
import numpy as np

try:
    import vectorbt as vbt
    print("[OK] vectorbt loaded\n")
except ImportError:
    print("[ERROR] vectorbt not installed!")
    sys.exit(1)

print("="*80)
print("DEBUG: VECTORBT METRICS TEST")
print("="*80)

# Create simple test data
dates = pd.date_range('2024-01-01', periods=100, freq='1H')
np.random.seed(42)
close_prices = 1.1000 + np.random.randn(100) * 0.001  # EUR_USD around 1.10

# Create simple entry signals (every 10 bars)
entries = np.zeros(100, dtype=bool)
entries[::10] = True

df = pd.DataFrame({
    'close': close_prices,
    'entries': entries
}, index=dates)

print(f"Test data: {len(df)} bars, {entries.sum()} entry signals\n")

# Test with TP=30 pips, SL=15 pips
TP_PIPS = 30
SL_PIPS = 15
POSITION_SIZE = 100
INITIAL_CAPITAL = 10000
pip_value = 0.0001

print(f"Config: TP={TP_PIPS} pips, SL={SL_PIPS} pips, Size=${POSITION_SIZE}\n")

# Run backtest
pf = vbt.Portfolio.from_signals(
    close=df['close'],
    entries=df['entries'],
    exits=False,
    tp_stop=TP_PIPS * pip_value,
    sl_stop=SL_PIPS * pip_value,
    init_cash=INITIAL_CAPITAL,
    size=POSITION_SIZE,
    size_type='amount',
    fees=0.0,
    freq='1H'
)

print("="*80)
print("RAW VECTORBT OUTPUTS:")
print("="*80)

# Test all metrics
print(f"Total Trades      : {pf.trades.count()}")
print(f"Winning Trades    : {pf.trades.winning.count()}")
print(f"Losing Trades     : {pf.trades.losing.count()}")
print(f"Win Rate          : {pf.trades.win_rate():.4f}")
print(f"Total Return (raw): {pf.total_return():.6f}")
print(f"Max Drawdown (raw): {pf.max_drawdown():.6f}")
print(f"Profit Factor     : {pf.trades.profit_factor():.4f}")
print(f"Total Profit      : ${pf.total_profit():.2f}")
print(f"Final Value       : ${pf.final_value():.2f}")
print(f"Sharpe Ratio      : {pf.sharpe_ratio():.4f}")

print("\n" + "="*80)
print("CONVERTED TO PERCENTAGES (OUR METHOD):")
print("="*80)
print(f"Total Return      : {pf.total_return() * 100:.2f}%")
print(f"Max Drawdown      : {pf.max_drawdown() * 100:.2f}%")

print("\n" + "="*80)
print("ANALYSIS:")
print("="*80)

# Check if drawdown is negative
dd_raw = pf.max_drawdown()
if dd_raw < 0:
    print(f"[WARN] Drawdown is NEGATIVE ({dd_raw:.6f})")
    print("       This means the account grew without drawdown!")
    print("       Should we use abs(drawdown)?")
else:
    print(f"[OK] Drawdown is positive ({dd_raw:.6f})")

# Check if return makes sense
ret_raw = pf.total_return()
profit = pf.total_profit()
expected_ret = profit / INITIAL_CAPITAL

print(f"\nReturn check:")
print(f"  vectorbt return   : {ret_raw:.6f} ({ret_raw*100:.2f}%)")
print(f"  Expected (profit/capital): {expected_ret:.6f} ({expected_ret*100:.2f}%)")
print(f"  Match: {'YES' if abs(ret_raw - expected_ret) < 0.0001 else 'NO'}")

# Get equity curve
print("\n" + "="*80)
print("EQUITY CURVE ANALYSIS:")
print("="*80)

equity = pf.value()
print(f"Starting equity: ${equity.iloc[0]:.2f}")
print(f"Final equity   : ${equity.iloc[-1]:.2f}")
print(f"Max equity     : ${equity.max():.2f}")
print(f"Min equity     : ${equity.min():.2f}")

# Calculate drawdown manually
running_max = equity.expanding().max()
drawdown_curve = (equity - running_max) / running_max
max_dd_manual = drawdown_curve.min()

print(f"\nManual DD calculation:")
print(f"  Max DD (manual) : {max_dd_manual:.6f} ({max_dd_manual*100:.2f}%)")
print(f"  Max DD (vectorbt): {pf.max_drawdown():.6f} ({pf.max_drawdown()*100:.2f}%)")
print(f"  Match: {'YES' if abs(max_dd_manual - pf.max_drawdown()) < 0.0001 else 'NO'}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

if dd_raw < 0:
    print("[ACTION REQUIRED]")
    print("  Drawdown is negative - we need to use abs() or investigate further!")
    print("  Recommendation: dd = abs(pf.max_drawdown()) * 100")
else:
    print("[OK] Metrics look correct, no changes needed")

print("\n" + "="*80)
print("TRADES DETAILS:")
print("="*80)

# Show first few trades
trades_df = pf.trades.records_readable
if len(trades_df) > 0:
    print(trades_df[['Entry Index', 'Exit Index', 'PnL', 'Return', 'Status']].head(10).to_string())
else:
    print("No trades executed!")

print("\n" + "="*80)
print("TEST COMPLETE!")
print("="*80)
