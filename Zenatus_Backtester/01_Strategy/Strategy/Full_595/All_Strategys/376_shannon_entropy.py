"""376 - Shannon Entropy Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ShannonEntropy:
    """Shannon Entropy - Measures market uncertainty/randomness"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_bins': {'default': 10, 'values': [5,10,15,20], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ShannonEntropy", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_bins = params.get('n_bins', 10)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Calculate Shannon Entropy
        entropy = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i]
            
            # Create histogram
            counts, bin_edges = np.histogram(window, bins=n_bins)
            
            # Probability distribution
            probs = counts / counts.sum()
            
            # Shannon entropy: H = -sum(p * log(p))
            entropy_val = 0
            for p in probs:
                if p > 0:
                    entropy_val -= p * np.log2(p)
            
            entropy.iloc[i] = entropy_val
        
        # Normalize (max entropy = log2(n_bins))
        max_entropy = np.log2(n_bins)
        entropy_normalized = entropy / max_entropy
        
        # Low entropy = predictable, High entropy = random
        # Signal: low entropy (predictable market)
        predictability = 1 - entropy_normalized
        
        # Smooth
        predictability_smooth = predictability.rolling(5).mean()
        
        # Entropy change (regime shift)
        entropy_change = entropy.diff().abs()
        
        return pd.DataFrame({
            'entropy': entropy,
            'entropy_normalized': entropy_normalized,
            'predictability': predictability,
            'predictability_smooth': predictability_smooth,
            'entropy_change': entropy_change
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High predictability (low entropy)
        entries = result['predictability_smooth'] > 0.6
        
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
            'signal_strength': result['predictability_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Predictable
        entries = result['predictability'] > 0.6
        
        # Exit: Unpredictable or regime shift
        exits = (result['predictability'] < 0.4) | (result['entropy_change'] > result['entropy_change'].rolling(20).mean() * 2)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('entropy_spike', index=data.index),
            'signal_strength': result['predictability_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['shannon_entropy'] = result['entropy']
        features['shannon_entropy_norm'] = result['entropy_normalized']
        features['shannon_predictability'] = result['predictability']
        features['shannon_predictability_smooth'] = result['predictability_smooth']
        features['shannon_entropy_change'] = result['entropy_change']
        features['shannon_low_entropy'] = (result['entropy_normalized'] < 0.5).astype(int)
        features['shannon_high_predictability'] = (result['predictability'] > 0.6).astype(int)
        
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

