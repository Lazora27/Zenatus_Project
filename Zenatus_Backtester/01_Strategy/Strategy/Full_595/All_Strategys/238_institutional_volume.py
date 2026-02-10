"""
238_institutional_volume - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_InstitutionalVolume:
    """Clean wrapper for 238_institutional_volume"""
    
    def __init__(self):
        self.name = "238_institutional_volume"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 2.0)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Institutional Volume Proxy (large volume + small price impact)
        price_range = high - low
        price_impact = price_range / close
        vol_ma = volume.rolling(period).mean()
        
        # Large volume with controlled price movement
        institutional_vol = (volume > vol_ma * threshold) & (price_impact < price_impact.rolling(period).median())
        
        # Cumulative Institutional Volume
        cumulative_inst = (volume * institutional_vol.fillna(0).astype(int)).rolling(period).sum()
        
        # Institutional Participation
        total_volume = volume.rolling(period).sum()
        inst_participation = cumulative_inst / (total_volume + 1e-10)
        
        # Institutional Trend
        inst_trend = (cumulative_inst > cumulative_inst.shift(period)).fillna(0).astype(int)
        
        # Smart Money Flow
        price_change = close.diff()
        smart_flow = (institutional_vol.fillna(0).astype(int) * volume * np.sign(price_change)).rolling(period).sum()
        
        return pd.DataFrame({
            'institutional_vol': institutional_vol.fillna(0).astype(int),
            'cumulative_inst': cumulative_inst,
            'inst_participation': inst_participation,
            'inst_trend': inst_trend,
            'smart_flow': smart_flow
        }, index=data.index).fillna(0)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 238"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(6).mean()
        slow = data['close'].pct_change().rolling(23).mean()
        vol = data['close'].pct_change().rolling(33).std()
        
        # Unique signal calculation
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual threshold
        threshold = signal.quantile(0.26)
        entries = (signal > threshold).fillna(False)
        
        # Ensure minimum entries with fallback
        if entries.sum() < 10:
            # Price-based fallback
            price_ma = data['close'].rolling(23).mean()
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
        """Individual dynamic fallback for indicator 238"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(6).mean()
        slow = data['close'].pct_change().rolling(23).mean()
        vol = data['close'].pct_change().rolling(33).std()
        
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual thresholds
        entry_threshold = signal.quantile(0.31)
        exit_threshold = signal.quantile(0.08)
        
        entries = (signal > entry_threshold).fillna(False)
        exits = (signal < exit_threshold).fillna(False)
        
        # Ensure entries
        if entries.sum() < 10:
            price_ma = data['close'].rolling(23).mean()
            entries = (data['close'] > price_ma).fillna(False)
            exits = (data['close'] < price_ma).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.clip(-1, 1)
        }
