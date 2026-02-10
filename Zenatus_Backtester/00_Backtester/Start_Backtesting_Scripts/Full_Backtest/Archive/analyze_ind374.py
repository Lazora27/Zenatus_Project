"""Analysiere Ind#374 FAILED Problem"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"/opt/Zenatus_Backtester\01_Strategy\Strategy\Unique\All_Strategys")))

import pandas as pd
import numpy as np

# Load indicator
from importlib import import_module
spec = __import__('374_adaptive_filter')
Indicator_AdaptiveFilter = spec.Indicator_AdaptiveFilter

# Create test data
dates = pd.date_range('2020-01-01', periods=1000, freq='1H')
test_data = pd.DataFrame({
    'open': np.random.randn(1000).cumsum() + 100,
    'high': np.random.randn(1000).cumsum() + 101,
    'low': np.random.randn(1000).cumsum() + 99,
    'close': np.random.randn(1000).cumsum() + 100,
    'volume': np.random.randint(1000, 10000, 1000)
}, index=dates)

# Test indicator
ind = Indicator_AdaptiveFilter()
params = {'period': 20, 'mu': 0.01, 'tp_pips': 50, 'sl_pips': 25}

print("Testing Ind#374 Adaptive Filter...")
print(f"Params: {params}")

try:
    # Test calculate
    result = ind.calculate(test_data, params)
    print(f"✅ calculate() works - {len(result)} rows")
    print(f"Columns: {result.columns.tolist()}")
    
    # Test generate_signals_fixed
    signals = ind.generate_signals_fixed(test_data, params)
    print(f"✅ generate_signals_fixed() works")
    print(f"Entries: {signals['entries'].sum()}")
    print(f"Exits: {signals['exits'].sum()}")
    
    if signals['entries'].sum() == 0:
        print("⚠️ WARNING: No entries generated!")
    
    print("\n✅ Ind#374 funktioniert korrekt!")
    
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
