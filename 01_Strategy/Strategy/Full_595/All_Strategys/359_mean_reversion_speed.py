"""359 - Mean Reversion Speed"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MeanReversionSpeed:
    """Mean Reversion Speed - Measures how fast price reverts to mean"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MeanReversionSpeed", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Mean
        mean = data['close'].rolling(period).mean()
        
        # Deviation from mean
        deviation = data['close'] - mean
        
        # Ornstein-Uhlenbeck process: dX = theta * (mu - X) * dt + sigma * dW
        # theta = mean reversion speed
        
        # Estimate theta using AR(1) on deviations
        theta = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            dev_window = deviation.iloc[i-period:i]
            
            # AR(1) coefficient
            ar_coef = dev_window.autocorr(lag=1)
            
            if not np.isnan(ar_coef):
                # theta = -log(phi) where phi is AR(1) coefficient
                if ar_coef > 0 and ar_coef < 1:
                    theta.iloc[i] = -np.log(ar_coef)
                else:
                    theta.iloc[i] = 0
        
        # Half-life of mean reversion
        half_life = np.log(2) / (theta + 1e-10)
        half_life = half_life.clip(0, 100)
        
        # Signal: fast mean reversion = good opportunity
        # Low half-life = fast reversion
        reversion_signal = 1 / (1 + half_life / 10)
        
        # Smooth
        reversion_smooth = reversion_signal.rolling(5).mean()
        
        # Current deviation (entry when far from mean)
        deviation_zscore = deviation / (data['close'].rolling(period).std() + 1e-10)
        
        return pd.DataFrame({
            'theta': theta,
            'half_life': half_life,
            'deviation': deviation,
            'deviation_zscore': deviation_zscore,
            'reversion_signal': reversion_signal,
            'reversion_smooth': reversion_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Fast mean reversion + below mean
        entries = (result['reversion_smooth'] > 0.6) & (result['deviation_zscore'] < -0.5)
        
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
            'signal_strength': result['reversion_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Below mean
        entries = result['deviation_zscore'] < -1
        
        # Exit: At mean
        exits = abs(result['deviation_zscore']) < 0.2
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('mean_reached', index=data.index),
            'signal_strength': result['reversion_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['mr_theta'] = result['theta']
        features['mr_half_life'] = result['half_life']
        features['mr_deviation'] = result['deviation']
        features['mr_deviation_zscore'] = result['deviation_zscore']
        features['mr_signal'] = result['reversion_signal']
        features['mr_smooth'] = result['reversion_smooth']
        features['mr_fast_reversion'] = (result['half_life'] < 10).astype(int)
        
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

