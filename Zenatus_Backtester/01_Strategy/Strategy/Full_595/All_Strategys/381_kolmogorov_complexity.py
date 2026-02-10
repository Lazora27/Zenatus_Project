"""381 - Kolmogorov Complexity"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_KolmogorovComplexity:
    """Kolmogorov Complexity - Measures algorithmic complexity via compression"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "KolmogorovComplexity", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Discretize price movements
        returns = data['close'].pct_change().fillna(0)
        
        # Binary encoding: 1 = up, 0 = down
        binary_sequence = (returns > 0).astype(int)
        
        # Approximate Kolmogorov complexity via compression ratio
        complexity = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = binary_sequence.iloc[i-period:i].values
            
            # Simple run-length encoding
            runs = []
            current_val = window[0]
            current_len = 1
            
            for j in range(1, len(window)):
                if window[j] == current_val:
                    current_len += 1
                else:
                    runs.append((current_val, current_len))
                    current_val = window[j]
                    current_len = 1
            
            runs.append((current_val, current_len))
            
            # Compression ratio
            original_length = len(window)
            compressed_length = len(runs)
            
            # Complexity (lower compression = higher complexity)
            if original_length > 0:
                complexity.iloc[i] = compressed_length / original_length
        
        # Normalize
        complexity_normalized = complexity.clip(0, 1)
        
        # Low complexity = predictable (high compression)
        predictability = 1 - complexity_normalized
        
        # Smooth
        predictability_smooth = predictability.rolling(5).mean()
        
        # Complexity change (regime shift)
        complexity_change = complexity.diff().abs()
        
        return pd.DataFrame({
            'complexity': complexity,
            'complexity_normalized': complexity_normalized,
            'predictability': predictability,
            'predictability_smooth': predictability_smooth,
            'complexity_change': complexity_change
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High predictability (low complexity)
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
        
        # Exit: Complex
        exits = result['predictability'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('complexity_increase', index=data.index),
            'signal_strength': result['predictability_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['kolmogorov_complexity'] = result['complexity']
        features['kolmogorov_complexity_norm'] = result['complexity_normalized']
        features['kolmogorov_predictability'] = result['predictability']
        features['kolmogorov_predictability_smooth'] = result['predictability_smooth']
        features['kolmogorov_complexity_change'] = result['complexity_change']
        features['kolmogorov_low_complexity'] = (result['complexity_normalized'] < 0.5).astype(int)
        
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

