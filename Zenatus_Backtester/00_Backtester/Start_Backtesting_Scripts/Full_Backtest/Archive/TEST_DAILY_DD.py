# -*- coding: utf-8 -*-
"""
TEST: Daily Drawdown Calculation
"""

import pandas as pd
import numpy as np
import vectorbt as vbt

print("="*80)
print("DAILY DRAWDOWN CALCULATION TEST")
print("="*80)

# Create test data
dates = pd.date_range('2024-01-01', periods=1000, freq='1H')
np.random.seed(42)
close_prices = 1.1000 + np.cumsum(np.random.randn(1000) * 0.0001)

# Create entry signals
entries = np.zeros(1000, dtype=bool)
entries[::50] = True  # Every 50 bars

df = pd.DataFrame({
    'close': close_prices
}, index=dates)

print(f"Test data: {len(df)} hours ({len(df)/24:.1f} days)\n")

# Run backtest
TP_PIPS = 30
SL_PIPS = 15
POSITION_SIZE = 100
INITIAL_CAPITAL = 10000
pip_value = 0.0001

pf = vbt.Portfolio.from_signals(
    close=df['close'],
    entries=entries,
    exits=False,
    tp_stop=TP_PIPS * pip_value,
    sl_stop=SL_PIPS * pip_value,
    init_cash=INITIAL_CAPITAL,
    size=POSITION_SIZE,
    size_type='amount',
    fees=0.0,
    freq='1H'
)

print("Backtest Results:")
print(f"  Trades: {pf.trades.count()}")
print(f"  Return: {pf.total_return() * 100:.2f}%")
print(f"  Max DD: {abs(pf.max_drawdown()) * 100:.4f}%\n")

# Get equity curve
equity = pf.value()
print(f"Equity curve: {len(equity)} points")
print(f"  Start: ${equity.iloc[0]:.2f}")
print(f"  End: ${equity.iloc[-1]:.2f}")
print(f"  Max: ${equity.max():.2f}")
print(f"  Min: ${equity.min():.2f}\n")

# Method 1: Daily equity resampling
print("="*80)
print("METHOD 1: Daily Equity Drawdown")
print("="*80)

equity_daily = equity.resample('D').last()
equity_daily = equity_daily.dropna()
print(f"Daily equity points: {len(equity_daily)}")

if len(equity_daily) > 1:
    # Calculate daily drawdowns
    cummax = equity_daily.expanding().max()
    daily_drawdowns = (equity_daily - cummax) / cummax
    max_daily_dd = abs(daily_drawdowns.min()) * 100
    
    print(f"\nDaily Drawdown Analysis:")
    print(f"  Max Daily DD: {max_daily_dd:.4f}%")
    print(f"  Worst day: {daily_drawdowns.idxmin()}")
    print(f"  Equity on worst day: ${equity_daily.loc[daily_drawdowns.idxmin()]:.2f}")
    
    # Show distribution
    print(f"\nDaily DD Distribution:")
    print(f"  Mean: {abs(daily_drawdowns.mean()) * 100:.4f}%")
    print(f"  Median: {abs(daily_drawdowns.median()) * 100:.4f}%")
    print(f"  Std: {daily_drawdowns.std() * 100:.4f}%")

# Method 2: Worst single-day return
print("\n" + "="*80)
print("METHOD 2: Worst Single-Day Loss")
print("="*80)

if len(equity_daily) > 1:
    daily_returns = equity_daily.pct_change().dropna()
    print(f"Daily returns: {len(daily_returns)}")
    
    worst_day_return = daily_returns.min()
    worst_day_loss = abs(worst_day_return) * 100
    
    print(f"\nWorst Single Day:")
    print(f"  Date: {daily_returns.idxmin()}")
    print(f"  Loss: {worst_day_loss:.4f}%")
    print(f"  Return: {worst_day_return * 100:.4f}%")
    
    print(f"\nDaily Return Stats:")
    print(f"  Mean: {daily_returns.mean() * 100:.4f}%")
    print(f"  Std: {daily_returns.std() * 100:.4f}%")
    print(f"  Best day: {daily_returns.max() * 100:.4f}%")
    print(f"  Worst day: {daily_returns.min() * 100:.4f}%")

# Method 3: Combined (conservative)
print("\n" + "="*80)
print("METHOD 3: Conservative Daily DD (max of both)")
print("="*80)

final_daily_dd = max(max_daily_dd, worst_day_loss)
print(f"\nFinal Daily Drawdown: {final_daily_dd:.4f}%")
print(f"  (Max of daily DD: {max_daily_dd:.4f}% and worst day: {worst_day_loss:.4f}%)")

# Comparison with overall max DD
overall_max_dd = abs(pf.max_drawdown()) * 100
print(f"\nComparison:")
print(f"  Overall Max DD: {overall_max_dd:.4f}%")
print(f"  Daily DD: {final_daily_dd:.4f}%")
print(f"  Ratio (Daily/Overall): {final_daily_dd/overall_max_dd:.2f}x")

# OLD METHOD (WRONG!)
print("\n" + "="*80)
print("OLD METHOD (WRONG!): max_dd / days")
print("="*80)

days = len(df) / 24
old_daily_dd = overall_max_dd / days
print(f"  Days: {days:.1f}")
print(f"  Max DD: {overall_max_dd:.4f}%")
print(f"  Old Daily DD: {old_daily_dd:.6f}%")
print(f"  This is WRONG! It's just average DD per day, not actual daily DD!")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print(f"Correct Daily DD: {final_daily_dd:.4f}%")
print(f"Wrong (old) Daily DD: {old_daily_dd:.6f}% <- Scientific notation risk!")
print(f"\nThe correct method is {final_daily_dd/old_daily_dd:.0f}x higher!")
print("="*80)
