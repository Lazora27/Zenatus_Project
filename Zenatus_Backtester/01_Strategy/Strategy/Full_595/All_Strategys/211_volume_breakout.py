"""
211_volume_breakout - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_VolumeBreakout:
    """Clean wrapper for 211_volume_breakout"""
    
    def __init__(self):
        self.name = "211_volume_breakout"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        vol_mult = params.get('vol_multiplier', 2.0)
        
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Volume Threshold
        vol_ma = volume.rolling(period).mean()
        vol_breakout = (volume > vol_ma * vol_mult).fillna(0).astype(int)
        
        # Price Breakout
        price_high = high.rolling(period).max()
        price_low = low.rolling(period).min()
        
        upper_breakout = (close > price_high.shift(1)).fillna(0).astype(int)
        lower_breakout = (close < price_low.shift(1)).fillna(0).astype(int)
        
        # Volume Confirmed Breakout
        vol_confirmed_up = (upper_breakout == 1) & (vol_breakout == 1)
        vol_confirmed_down = (lower_breakout == 1) & (vol_breakout == 1)
        
        # Breakout Strength
        breakout_strength = volume / vol_ma
        
        return pd.DataFrame({
            'vol_breakout': vol_breakout,
            'upper_breakout': upper_breakout,
            'vol_confirmed_up': vol_confirmed_up.fillna(0).astype(int),
            'vol_confirmed_down': vol_confirmed_down.fillna(0).astype(int),
            'breakout_strength': breakout_strength
        }, index=data.index).fillna(0)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 211"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(4).mean()
        slow = data['close'].pct_change().rolling(16).mean()
        vol = data['close'].pct_change().rolling(21).std()
        
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
        """Individual dynamic fallback for indicator 211"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(4).mean()
        slow = data['close'].pct_change().rolling(16).mean()
        vol = data['close'].pct_change().rolling(21).std()
        
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
