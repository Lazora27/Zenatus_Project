"""300 - Probability Distribution Analysis"""
import numpy as np
import pandas as pd

from typing import Dict
from scipy import stats
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ProbabilityDistribution:
    """Probability Distribution - Analyzes return distribution"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ProbabilityDistribution", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate returns
        returns = np.log(data['close'] / data['close'].shift(1))
        
        # Rolling statistics
        returns_mean = returns.rolling(period).mean()
        returns_std = returns.rolling(period).std()
        
        # Skewness and Kurtosis
        returns_skew = returns.rolling(period).skew()
        returns_kurt = returns.rolling(period).kurt()
        
        # Z-score
        returns_zscore = (returns - returns_mean) / (returns_std + 1e-10)
        
        # Probability of positive return
        prob_positive = returns.rolling(period).apply(lambda x: (x > 0).sum() / len(x))
        
        # Expected return
        expected_return = returns_mean
        
        # Value at Risk (95%)
        var_95 = returns.rolling(period).quantile(0.05)
        
        # Conditional VaR (CVaR)
        def calc_cvar(x):
            var = np.percentile(x, 5)
            return x[x <= var].mean()
        
        cvar_95 = returns.rolling(period).apply(calc_cvar, raw=True)
        
        return pd.DataFrame({
            'returns_mean': returns_mean,
            'returns_std': returns_std,
            'returns_skew': returns_skew,
            'returns_kurt': returns_kurt,
            'returns_zscore': returns_zscore,
            'prob_positive': prob_positive,
            'expected_return': expected_return,
            'var_95': var_95,
            'cvar_95': cvar_95
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High probability of positive return
        entries = result['prob_positive'] > 0.6
        
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
            'signal_strength': result['prob_positive']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High probability of positive return
        entries = result['prob_positive'] > 0.6
        
        # Exit: Low probability
        exits = result['prob_positive'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('prob_change', index=data.index),
            'signal_strength': result['prob_positive']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['returns_mean'] = result['returns_mean']
        features['returns_std'] = result['returns_std']
        features['returns_skew'] = result['returns_skew']
        features['returns_kurt'] = result['returns_kurt']
        features['returns_zscore'] = result['returns_zscore']
        features['prob_positive'] = result['prob_positive']
        features['expected_return'] = result['expected_return']
        features['var_95'] = result['var_95']
        features['cvar_95'] = result['cvar_95']
        features['sharpe_estimate'] = result['returns_mean'] / (result['returns_std'] + 1e-10)
        
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

