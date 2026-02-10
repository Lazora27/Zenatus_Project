"""383 - Permutation Entropy"""
import numpy as np
import pandas as pd

from typing import Dict
from itertools import permutations
import math
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PermutationEntropy:
    """Permutation Entropy - Measures complexity via ordinal patterns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'order': {'default': 3, 'values': [3,4,5], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PermutationEntropy", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        order = params.get('order', 3)
        
        # Price series
        price = data['close'].values
        
        # Permutation Entropy
        perm_entropy = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = price[i-period:i]
            
            # Extract ordinal patterns
            patterns = []
            
            for j in range(len(window) - order + 1):
                # Get order-length subsequence
                subseq = window[j:j+order]
                
                # Get ordinal pattern (rank)
                pattern = tuple(np.argsort(subseq))
                patterns.append(pattern)
            
            # Count pattern frequencies
            unique_patterns, counts = np.unique(patterns, axis=0, return_counts=True)
            
            # Probability distribution
            probs = counts / counts.sum()
            
            # Permutation entropy
            pe = 0
            for p in probs:
                if p > 0:
                    pe -= p * np.log2(p)
            
            # Normalize by max entropy
            max_entropy = np.log2(math.factorial(order))
            perm_entropy.iloc[i] = pe / max_entropy if max_entropy > 0 else 0
        
        # Low entropy = regular patterns
        regularity = 1 - perm_entropy
        
        # Smooth
        regularity_smooth = regularity.rolling(5).mean()
        
        # Entropy change
        entropy_change = perm_entropy.diff().abs()
        
        return pd.DataFrame({
            'perm_entropy': perm_entropy,
            'regularity': regularity,
            'regularity_smooth': regularity_smooth,
            'entropy_change': entropy_change
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
            'exit_reason': pd.Series('pattern_irregular', index=data.index),
            'signal_strength': result['regularity_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['perm_entropy'] = result['perm_entropy']
        features['perm_regularity'] = result['regularity']
        features['perm_regularity_smooth'] = result['regularity_smooth']
        features['perm_entropy_change'] = result['entropy_change']
        features['perm_high_regularity'] = (result['regularity'] > 0.6).astype(int)
        
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

