"""379 - Approximate Entropy"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ApproximateEntropy:
    """Approximate Entropy - Measures regularity and unpredictability"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'm': {'default': 2, 'values': [2,3], 'optimize': False},
        'r': {'default': 0.2, 'values': [0.1,0.2,0.3], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ApproximateEntropy", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        m = params.get('m', 2)  # Pattern length
        r = params.get('r', 0.2)  # Tolerance
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Approximate Entropy (ApEn)
        apen = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i].values
            
            # Normalize
            std = window.std()
            if std > 0:
                window_norm = (window - window.mean()) / std
                tolerance = r * std
            else:
                window_norm = window
                tolerance = r
            
            # Calculate ApEn
            N = len(window_norm)
            
            def _maxdist(x_i, x_j, m):
                """Maximum distance between patterns"""
                return max([abs(x_i[k] - x_j[k]) for k in range(m)])
            
            def _phi(m):
                """Pattern matching function"""
                patterns = N - m + 1
                C = []
                
                for i_pat in range(patterns):
                    pattern_i = window_norm[i_pat:i_pat+m]
                    matches = 0
                    
                    for j_pat in range(patterns):
                        pattern_j = window_norm[j_pat:j_pat+m]
                        
                        if _maxdist(pattern_i, pattern_j, m) <= tolerance:
                            matches += 1
                    
                    C.append(matches / patterns)
                
                return sum([np.log(c) for c in C if c > 0]) / patterns
            
            try:
                phi_m = _phi(m)
                phi_m1 = _phi(m + 1)
                apen.iloc[i] = phi_m - phi_m1
            except:
                apen.iloc[i] = 0
        
        # Normalize
        apen_normalized = apen / (apen.rolling(50).max() + 1e-10)
        apen_normalized = apen_normalized.clip(0, 1)
        
        # Low ApEn = regular/predictable
        regularity = 1 - apen_normalized
        
        # Smooth
        regularity_smooth = regularity.rolling(5).mean()
        
        return pd.DataFrame({
            'apen': apen,
            'apen_normalized': apen_normalized,
            'regularity': regularity,
            'regularity_smooth': regularity_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High regularity
        entries = result['regularity_smooth'] > 0.6
        
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
            'signal_strength': result['regularity_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Regular
        entries = result['regularity'] > 0.6
        
        # Exit: Irregular
        exits = result['regularity'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('irregularity', index=data.index),
            'signal_strength': result['regularity_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['apen_value'] = result['apen']
        features['apen_normalized'] = result['apen_normalized']
        features['apen_regularity'] = result['regularity']
        features['apen_regularity_smooth'] = result['regularity_smooth']
        features['apen_high_regularity'] = (result['regularity'] > 0.6).astype(int)
        
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

