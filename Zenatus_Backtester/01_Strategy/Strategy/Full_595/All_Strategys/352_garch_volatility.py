"""352 - GARCH Volatility Forecast"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_GARCHVolatility:
    """GARCH Volatility - Generalized Autoregressive Conditional Heteroskedasticity"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "GARCHVolatility", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Simplified GARCH(1,1): sigma^2_t = omega + alpha * r^2_{t-1} + beta * sigma^2_{t-1}
        omega = 0.0001
        alpha = 0.1
        beta = 0.85
        
        # Initialize
        variance = returns.rolling(period).var().fillna(returns.var())
        
        garch_variance = pd.Series(variance.iloc[0], index=data.index)
        
        for i in range(1, len(data)):
            # GARCH update
            garch_variance.iloc[i] = (omega + 
                                     alpha * returns.iloc[i-1]**2 + 
                                     beta * garch_variance.iloc[i-1])
        
        # Volatility forecast
        garch_volatility = np.sqrt(garch_variance)
        
        # Volatility regime
        vol_ma = garch_volatility.rolling(period).mean()
        vol_std = garch_volatility.rolling(period).std()
        
        # High volatility = risky, Low volatility = opportunity
        vol_zscore = (garch_volatility - vol_ma) / (vol_std + 1e-10)
        
        # Signal: enter when volatility is low
        vol_signal = (vol_zscore < 0).astype(float)
        
        # Smooth
        vol_smooth = vol_signal.rolling(5).mean()
        
        # Volatility persistence
        persistence = garch_volatility.rolling(10).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0
        )
        
        return pd.DataFrame({
            'garch_variance': garch_variance,
            'garch_volatility': garch_volatility,
            'vol_zscore': vol_zscore,
            'vol_signal': vol_signal,
            'vol_smooth': vol_smooth,
            'persistence': persistence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low volatility regime
        entries = result['vol_smooth'] > 0.6
        
        # Manual TP/SL
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': result['vol_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low volatility
        entries = result['vol_smooth'] > 0.6
        
        # Exit: High volatility
        exits = result['vol_zscore'] > 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('volatility_spike', index=data.index),
            'signal_strength': result['vol_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['garch_variance'] = result['garch_variance']
        features['garch_volatility'] = result['garch_volatility']
        features['garch_vol_zscore'] = result['vol_zscore']
        features['garch_signal'] = result['vol_signal']
        features['garch_smooth'] = result['vol_smooth']
        features['garch_persistence'] = result['persistence']
        features['garch_low_vol'] = (result['vol_zscore'] < 0).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass

    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100, 150],
            'sl_pips': [15, 25, 35, 50, 75]
        }

