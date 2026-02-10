"""394 - Bifurcation Detector"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BifurcationDetector:
    """Bifurcation Detector - Detects regime changes and bifurcations"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BifurcationDetector", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Bifurcation indicators
        variance_ratio = pd.Series(0.0, index=data.index)
        distribution_change = pd.Series(0.0, index=data.index)
        
        for i in range(period * 2, len(data)):
            # Compare two consecutive windows
            window1 = returns.iloc[i-period*2:i-period]
            window2 = returns.iloc[i-period:i]
            
            # Variance ratio (sudden change in variance = bifurcation)
            var1 = window1.var()
            var2 = window2.var()
            
            if var1 > 0:
                variance_ratio.iloc[i] = abs(var2 - var1) / var1
            
            # Distribution change (KS-test-like)
            # Compare empirical CDFs
            combined = np.concatenate([window1.values, window2.values])
            combined_sorted = np.sort(combined)
            
            cdf1 = np.searchsorted(np.sort(window1.values), combined_sorted, side='right') / len(window1)
            cdf2 = np.searchsorted(np.sort(window2.values), combined_sorted, side='right') / len(window2)
            
            # Maximum difference
            ks_stat = np.max(np.abs(cdf1 - cdf2))
            distribution_change.iloc[i] = ks_stat
        
        # Bifurcation score (high = regime change)
        bifurcation_score = (variance_ratio + distribution_change) / 2
        
        # Detect bifurcation points
        threshold = bifurcation_score.rolling(50).quantile(0.8)
        is_bifurcation = (bifurcation_score > threshold).astype(int)
        
        # Signal: after bifurcation (new regime)
        post_bifurcation = is_bifurcation.shift(1).fillna(0)
        
        # Smooth
        post_bifurcation_smooth = post_bifurcation.rolling(5).mean()
        
        return pd.DataFrame({
            'variance_ratio': variance_ratio,
            'distribution_change': distribution_change,
            'bifurcation_score': bifurcation_score,
            'is_bifurcation': is_bifurcation,
            'post_bifurcation': post_bifurcation,
            'post_bifurcation_smooth': post_bifurcation_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: After bifurcation (new regime)
        entries = result['post_bifurcation_smooth'] > 0.3
        
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
            'signal_strength': result['post_bifurcation_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Post-bifurcation
        entries = result['post_bifurcation'] > 0.5
        
        # Exit: Next bifurcation
        exits = result['is_bifurcation'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('new_bifurcation', index=data.index),
            'signal_strength': result['post_bifurcation_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['bifurcation_variance_ratio'] = result['variance_ratio']
        features['bifurcation_distribution_change'] = result['distribution_change']
        features['bifurcation_score'] = result['bifurcation_score']
        features['bifurcation_is_bifurcation'] = result['is_bifurcation']
        features['bifurcation_post'] = result['post_bifurcation']
        features['bifurcation_post_smooth'] = result['post_bifurcation_smooth']
        features['bifurcation_detected'] = (result['is_bifurcation'] == 1).astype(int)
        
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

