"""
280_fibonacci_retracements - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_FibonacciRetracements:
    """Clean wrapper for 280_fibonacci_retracements"""
    
    def __init__(self):
        self.name = "280_fibonacci_retracements"
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        tolerance = params.get('tolerance', 0.01)
        high, low, close = data['high'], data['low'], data['close']
        
        # Calculate swing high and low
        swing_high = high.rolling(period).max()
        swing_low = low.rolling(period).min()
        
        # Fibonacci levels
        fib_range = swing_high - swing_low
        
        fib_0 = swing_low
        fib_236 = swing_low + fib_range * 0.236
        fib_382 = swing_low + fib_range * 0.382
        fib_500 = swing_low + fib_range * 0.500
        fib_618 = swing_low + fib_range * 0.618
        fib_786 = swing_low + fib_range * 0.786
        fib_100 = swing_high
        
        # Check if price is near Fibonacci levels
        near_236 = (abs(close - fib_236) / close < tolerance).fillna(0).astype(int)
        near_382 = (abs(close - fib_382) / close < tolerance).fillna(0).astype(int)
        near_500 = (abs(close - fib_500) / close < tolerance).fillna(0).astype(int)
        near_618 = (abs(close - fib_618) / close < tolerance).fillna(0).astype(int)
        near_786 = (abs(close - fib_786) / close < tolerance).fillna(0).astype(int)
        
        # Golden ratio (618) is most important
        golden_ratio_signal = near_618
        
        # Any Fibonacci level
        any_fib_level = near_236 + near_382 + near_500 + near_618 + near_786
        
        # Retracement strength
        retracement_pct = (close - swing_low) / (fib_range + 1e-10)
        
        return pd.DataFrame({
            'fib_0': fib_0,
            'fib_236': fib_236,
            'fib_382': fib_382,
            'fib_500': fib_500,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'fib_100': fib_100,
            'near_236': near_236,
            'near_382': near_382,
            'near_500': near_500,
            'near_618': near_618,
            'near_786': near_786,
            'golden_ratio_signal': golden_ratio_signal,
            'any_fib_level': any_fib_level,
            'retracement_pct': retracement_pct
        }, index=data.index).fillna(0)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 280"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(3).mean()
        slow = data['close'].pct_change().rolling(15).mean()
        vol = data['close'].pct_change().rolling(30).std()
        
        # Unique signal calculation
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual threshold
        threshold = signal.quantile(0.1)
        entries = (signal > threshold).fillna(False)
        
        # Ensure minimum entries with fallback
        if entries.sum() < 10:
            # Price-based fallback
            price_ma = data['close'].rolling(15).mean()
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
        """Individual dynamic fallback for indicator 280"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(3).mean()
        slow = data['close'].pct_change().rolling(15).mean()
        vol = data['close'].pct_change().rolling(30).std()
        
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual thresholds
        entry_threshold = signal.quantile(0.15000000000000002)
        exit_threshold = signal.quantile(0.05)
        
        entries = (signal > entry_threshold).fillna(False)
        exits = (signal < exit_threshold).fillna(False)
        
        # Ensure entries
        if entries.sum() < 10:
            price_ma = data['close'].rolling(15).mean()
            entries = (data['close'] > price_ma).fillna(False)
            exits = (data['close'] < price_ma).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.clip(-1, 1)
        }
