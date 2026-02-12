"""397 - Recurrence Quantification Analysis"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RecurrenceQuantification:
    """Recurrence Quantification Analysis - RQA metrics"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 0.1, 'values': [0.05,0.1,0.15], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RecurrenceQuantification", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 0.1)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # RQA metrics
        laminarity = pd.Series(0.0, index=data.index)
        trapping_time = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i].values
            
            # Normalize
            if window.std() > 0:
                window_norm = (window - window.mean()) / window.std()
            else:
                window_norm = window
            
            # Recurrence matrix
            n = len(window_norm)
            recurrence_matrix = np.zeros((n, n))
            
            for j in range(n):
                for k in range(n):
                    if abs(window_norm[j] - window_norm[k]) < threshold:
                        recurrence_matrix[j, k] = 1
            
            # Laminarity (vertical lines)
            vertical_points = 0
            
            for col in range(n):
                column = recurrence_matrix[:, col]
                
                # Count consecutive 1s
                line_length = 0
                for val in column:
                    if val == 1:
                        line_length += 1
                    else:
                        if line_length >= 2:
                            vertical_points += line_length
                        line_length = 0
                
                if line_length >= 2:
                    vertical_points += line_length
            
            total_recurrent = recurrence_matrix.sum()
            laminarity.iloc[i] = vertical_points / total_recurrent if total_recurrent > 0 else 0
            
            # Trapping time (average length of vertical lines)
            vertical_lengths = []
            
            for col in range(n):
                column = recurrence_matrix[:, col]
                line_length = 0
                
                for val in column:
                    if val == 1:
                        line_length += 1
                    else:
                        if line_length >= 2:
                            vertical_lengths.append(line_length)
                        line_length = 0
                
                if line_length >= 2:
                    vertical_lengths.append(line_length)
            
            trapping_time.iloc[i] = np.mean(vertical_lengths) if len(vertical_lengths) > 0 else 0
        
        # High laminarity = laminar flow = predictable
        predictability = laminarity
        
        # Smooth
        predictability_smooth = predictability.rolling(5).mean()
        
        return pd.DataFrame({
            'laminarity': laminarity,
            'trapping_time': trapping_time,
            'predictability': predictability,
            'predictability_smooth': predictability_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High laminarity
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
        
        # Entry: Laminar
        entries = result['laminarity'] > 0.6
        
        # Exit: Turbulent
        exits = result['laminarity'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('turbulence', index=data.index),
            'signal_strength': result['predictability_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['rqa_laminarity'] = result['laminarity']
        features['rqa_trapping_time'] = result['trapping_time']
        features['rqa_predictability'] = result['predictability']
        features['rqa_predictability_smooth'] = result['predictability_smooth']
        features['rqa_laminar'] = (result['laminarity'] > 0.6).astype(int)
        
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

