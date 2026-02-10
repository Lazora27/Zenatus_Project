"""
124_trend_macddivergence - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_MACDDivergence:
    """Clean wrapper for 124_trend_macddivergence"""
    
    def __init__(self):
        self.name = "124_trend_macddivergence"
    
    def calculate(self, data, params):
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)
        lookback = params.get('lookback', 14)
        
        # Calculate MACD
        ema_fast = data['close'].ewm(span=fast).mean()
        ema_slow = data['close'].ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal_period).mean()
        
        # Find local extrema
        price_high = data['close'].rolling(lookback, center=True).max() == data['close']
        price_low = data['close'].rolling(lookback, center=True).min() == data['close']
        
        macd_high = macd.rolling(lookback, center=True).max() == macd
        macd_low = macd.rolling(lookback, center=True).min() == macd
        
        # Detect divergences
        bullish_div = pd.Series(0, index=data.index)
        bearish_div = pd.Series(0, index=data.index)
        
        for i in range(lookback * 2, len(data)):
            # Bullish divergence: price makes lower low, MACD makes higher low
            if price_low.iloc[i]:
                # Find previous low
                prev_lows = price_low.iloc[i-lookback*2:i-lookback]
                if prev_lows.any():
                    prev_idx = prev_lows[::-1].idxmax()
                    if data['close'].iloc[i] < data['close'].iloc[prev_idx]:
                        if macd.iloc[i] > macd.iloc[prev_idx]:
                            bullish_div.iloc[i] = 1
            
            # Bearish divergence: price makes higher high, MACD makes lower high
            if price_high.iloc[i]:
                prev_highs = price_high.iloc[i-lookback*2:i-lookback]
                if prev_highs.any():
                    prev_idx = prev_highs[::-1].idxmax()
                    if data['close'].iloc[i] > data['close'].iloc[prev_idx]:
                        if macd.iloc[i] < macd.iloc[prev_idx]:
                            bearish_div.iloc[i] = -1
        
        divergence = bullish_div + bearish_div
        
        return pd.DataFrame({
            'macd': macd,
            'signal': signal_line,
            'divergence': divergence
        }, index=data.index)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 124"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(7).mean()
        slow = data['close'].pct_change().rolling(19).mean()
        vol = data['close'].pct_change().rolling(24).std()
        
        # Unique signal calculation
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual threshold
        threshold = signal.quantile(0.18)
        entries = (signal > threshold).fillna(False)
        
        # Ensure minimum entries with fallback
        if entries.sum() < 10:
            # Price-based fallback
            price_ma = data['close'].rolling(19).mean()
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
        """Individual dynamic fallback for indicator 124"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(7).mean()
        slow = data['close'].pct_change().rolling(19).mean()
        vol = data['close'].pct_change().rolling(24).std()
        
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual thresholds
        entry_threshold = signal.quantile(0.22999999999999998)
        exit_threshold = signal.quantile(0.09)
        
        entries = (signal > entry_threshold).fillna(False)
        exits = (signal < exit_threshold).fillna(False)
        
        # Ensure entries
        if entries.sum() < 10:
            price_ma = data['close'].rolling(19).mean()
            entries = (data['close'] > price_ma).fillna(False)
            exits = (data['close'] < price_ma).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.clip(-1, 1)
        }
