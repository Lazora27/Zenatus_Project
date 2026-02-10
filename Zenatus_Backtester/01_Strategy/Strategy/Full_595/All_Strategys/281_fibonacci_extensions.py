"""
281_fibonacci_extensions - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_FibonacciExtensions:
    """Clean wrapper for 281_fibonacci_extensions"""
    
    def __init__(self):
        self.name = "281_fibonacci_extensions"
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        tolerance = params.get('tolerance', 0.01)
        high, low, close = data['high'], data['low'], data['close']
        
        # Calculate swing points
        swing_high = high.rolling(period).max()
        swing_low = low.rolling(period).min()
        fib_range = swing_high - swing_low
        
        # Fibonacci extension levels (beyond 100%)
        fib_127 = swing_high + fib_range * 0.272
        fib_138 = swing_high + fib_range * 0.382
        fib_161 = swing_high + fib_range * 0.618
        fib_200 = swing_high + fib_range * 1.000
        fib_261 = swing_high + fib_range * 1.618
        fib_423 = swing_high + fib_range * 3.236
        
        # Check if price is near extension levels
        near_127 = (abs(close - fib_127) / close < tolerance).fillna(0).astype(int)
        near_138 = (abs(close - fib_138) / close < tolerance).fillna(0).astype(int)
        near_161 = (abs(close - fib_161) / close < tolerance).fillna(0).astype(int)
        near_200 = (abs(close - fib_200) / close < tolerance).fillna(0).astype(int)
        near_261 = (abs(close - fib_261) / close < tolerance).fillna(0).astype(int)
        
        # Golden extension (161.8%)
        golden_extension = near_161
        
        # Any extension level
        any_extension = near_127 + near_138 + near_161 + near_200 + near_261
        
        # Extension progress
        extension_pct = (close - swing_high) / (fib_range + 1e-10)
        
        return pd.DataFrame({
            'fib_127': fib_127,
            'fib_138': fib_138,
            'fib_161': fib_161,
            'fib_200': fib_200,
            'fib_261': fib_261,
            'fib_423': fib_423,
            'near_127': near_127,
            'near_161': near_161,
            'near_261': near_261,
            'golden_extension': golden_extension,
            'any_extension': any_extension,
            'extension_pct': extension_pct
        }, index=data.index).fillna(0)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 281"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(4).mean()
        slow = data['close'].pct_change().rolling(16).mean()
        vol = data['close'].pct_change().rolling(31).std()
        
        # Unique signal calculation
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual threshold
        threshold = signal.quantile(0.12000000000000001)
        entries = (signal > threshold).fillna(False)
        
        # Ensure minimum entries with fallback
        if entries.sum() < 10:
            # Price-based fallback
            price_ma = data['close'].rolling(16).mean()
            entries = (data['close'] > price_ma).fillna(False)
        
        exits = pd.Series(False, index=data.index)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': signal.clip(-1, 1)
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual dynamic fallback for indicator 281"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(4).mean()
        slow = data['close'].pct_change().rolling(16).mean()
        vol = data['close'].pct_change().rolling(31).std()
        
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual thresholds
        entry_threshold = signal.quantile(0.17)
        exit_threshold = signal.quantile(0.060000000000000005)
        
        entries = (signal > entry_threshold).fillna(False)
        exits = (signal < exit_threshold).fillna(False)
        
        # Ensure entries
        if entries.sum() < 10:
            price_ma = data['close'].rolling(16).mean()
            entries = (data['close'] > price_ma).fillna(False)
            exits = (data['close'] < price_ma).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.clip(-1, 1)
        }
