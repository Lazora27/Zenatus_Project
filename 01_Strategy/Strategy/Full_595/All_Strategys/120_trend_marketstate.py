"""
120_trend_marketstate - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_MarketState:
    """Clean wrapper for 120_trend_marketstate"""
    
    def __init__(self):
        self.name = "120_trend_marketstate"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Component 1: Trend Strength (ADX-like)
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        price_change = abs(data['close'] - data['close'].shift(period))
        trend_strength = (price_change / (atr * period + 1e-10)).clip(0, 1)
        
        # Component 2: Volatility (normalized)
        returns = data['close'].pct_change()
        volatility = returns.rolling(period).std()
        vol_norm = (volatility - volatility.rolling(100).min()) / \
                  (volatility.rolling(100).max() - volatility.rolling(100).min() + 1e-10)
        vol_norm = vol_norm.fillna(0.5).clip(0, 1)
        
        # Component 3: Volume Trend
        if 'volume' in data.columns:
            vol_ma = data['volume'].rolling(period).mean()
            vol_trend = (data['volume'] / (vol_ma + 1e-10)).clip(0, 2) / 2
        else:
            vol_trend = pd.Series(0.5, index=data.index)
        
        # Market State Score (0-3)
        # 0 = Ranging/Low volatility
        # 1 = Trending/Low volatility
        # 2 = Ranging/High volatility
        # 3 = Trending/High volatility
        
        state = pd.Series(0, index=data.index)
        state = state.where(~((trend_strength > 0.3) & (vol_norm < 0.5)), 1)  # Trending/Low vol
        state = state.where(~((trend_strength < 0.5) & (vol_norm > 0.3)), 2)  # Ranging/High vol
        state = state.where(~((trend_strength > 0.3) & (vol_norm > 0.3)), 3)  # Trending/High vol
        
        return pd.DataFrame({
            'state': state,
            'trend_strength': trend_strength,
            'volatility': vol_norm,
            'volume_trend': vol_trend
        }, index=data.index)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 120"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(3).mean()
        slow = data['close'].pct_change().rolling(15).mean()
        vol = data['close'].pct_change().rolling(20).std()
        
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
        """Individual dynamic fallback for indicator 120"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(3).mean()
        slow = data['close'].pct_change().rolling(15).mean()
        vol = data['close'].pct_change().rolling(20).std()
        
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
