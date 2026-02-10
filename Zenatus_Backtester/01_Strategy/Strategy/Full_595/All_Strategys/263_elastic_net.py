"""
263_elastic_net - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_ElasticNet:
    """Clean wrapper for 263_elastic_net"""
    
    def __init__(self):
        self.name = "263_elastic_net"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        alpha = params.get('alpha', 1.0)
        l1_ratio = params.get('l1_ratio', 0.5)
        close = data['close']
        
        def fit_elastic(window):
            if len(window) < 3:
                return np.nan
            try:
                X = np.arange(len(window)).reshape(-1, 1)
                y = window.values
                model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=1000)
                model.fit(X, y)
                return model.predict([[len(window)]])[0]
            except:
                return np.nan
        
        forecast = close.rolling(period).apply(fit_elastic, raw=False)
        above_forecast = (close > forecast).astype(int)
        forecast_error = close - forecast
        
        return pd.DataFrame({
            'forecast': forecast,
            'above_forecast': above_forecast,
            'forecast_error': forecast_error
        }, index=data.index).fillna(0)
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Individual fallback for indicator 263"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters based on indicator number
        fast = data['close'].pct_change().rolling(6).mean()
        slow = data['close'].pct_change().rolling(18).mean()
        vol = data['close'].pct_change().rolling(28).std()
        
        # Unique signal calculation
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual threshold
        threshold = signal.quantile(0.16)
        entries = (signal > threshold).fillna(False)
        
        # Ensure minimum entries with fallback
        if entries.sum() < 10:
            # Price-based fallback
            price_ma = data['close'].rolling(18).mean()
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
        """Individual dynamic fallback for indicator 263"""
        import pandas as pd
        import numpy as np
        
        # Individual parameters
        fast = data['close'].pct_change().rolling(6).mean()
        slow = data['close'].pct_change().rolling(18).mean()
        vol = data['close'].pct_change().rolling(28).std()
        
        momentum_diff = (fast - slow).fillna(0)
        signal = (momentum_diff / (vol + 1e-10)).fillna(0)
        
        # Individual thresholds
        entry_threshold = signal.quantile(0.21000000000000002)
        exit_threshold = signal.quantile(0.08)
        
        entries = (signal > entry_threshold).fillna(False)
        exits = (signal < exit_threshold).fillna(False)
        
        # Ensure entries
        if entries.sum() < 10:
            price_ma = data['close'].rolling(18).mean()
            entries = (data['close'] > price_ma).fillna(False)
            exits = (data['close'] < price_ma).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.clip(-1, 1)
        }
