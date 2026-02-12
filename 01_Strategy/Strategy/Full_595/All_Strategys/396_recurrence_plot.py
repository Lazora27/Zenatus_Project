"""396 - Recurrence Plot Analysis"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RecurrencePlot:
    """Recurrence Plot - Detects recurring states in phase space"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RecurrencePlot", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 0.1)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Recurrence analysis
        recurrence_rate = pd.Series(0.0, index=data.index)
        determinism = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i].values
            
            # Normalize
            if window.std() > 0:
                window_norm = (window - window.mean()) / window.std()
            else:
                window_norm = window
            
            # Build recurrence matrix
            n = len(window_norm)
            recurrence_matrix = np.zeros((n, n))
            
            for j in range(n):
                for k in range(n):
                    dist = abs(window_norm[j] - window_norm[k])
                    if dist < threshold:
                        recurrence_matrix[j, k] = 1
            
            # Recurrence rate (density of recurrence matrix)
            recurrence_rate.iloc[i] = recurrence_matrix.sum() / (n * n)
            
            # Determinism (ratio of recurrent points forming diagonal lines)
            # Count diagonal lines of length >= 2
            diagonal_points = 0
            
            for diag in range(-n+1, n):
                diagonal = np.diagonal(recurrence_matrix, offset=diag)
                
                # Count consecutive 1s
                line_length = 0
                for val in diagonal:
                    if val == 1:
                        line_length += 1
                    else:
                        if line_length >= 2:
                            diagonal_points += line_length
                        line_length = 0
                
                if line_length >= 2:
                    diagonal_points += line_length
            
            total_recurrent = recurrence_matrix.sum()
            determinism.iloc[i] = diagonal_points / total_recurrent if total_recurrent > 0 else 0
        
        # High determinism = predictable
        predictability = determinism
        
        # Smooth
        predictability_smooth = predictability.rolling(5).mean()
        
        return pd.DataFrame({
            'recurrence_rate': recurrence_rate,
            'determinism': determinism,
            'predictability': predictability,
            'predictability_smooth': predictability_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High determinism
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
        
        # Entry: Deterministic
        entries = result['determinism'] > 0.6
        
        # Exit: Stochastic
        exits = result['determinism'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('recurrence_loss', index=data.index),
            'signal_strength': result['predictability_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['recurrence_rate'] = result['recurrence_rate']
        features['recurrence_determinism'] = result['determinism']
        features['recurrence_predictability'] = result['predictability']
        features['recurrence_predictability_smooth'] = result['predictability_smooth']
        features['recurrence_high_determinism'] = (result['determinism'] > 0.6).astype(int)
        
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

