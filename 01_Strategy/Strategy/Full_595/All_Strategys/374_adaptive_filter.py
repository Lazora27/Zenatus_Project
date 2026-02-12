"""374 - Adaptive Filter (LMS)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AdaptiveFilter:
    """Adaptive Filter - Least Mean Squares adaptive filtering"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'mu': {'default': 0.01, 'values': [0.001,0.01,0.05,0.1], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AdaptiveFilter", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        mu = params.get('mu', 0.01)  # Learning rate
        
        # LMS adaptive filter
        price = data['close'].values
        
        # Filter order
        M = 5
        
        # Initialize weights
        w = np.zeros(M)
        
        # Filtered output
        filtered = np.zeros(len(price))
        prediction_error = np.zeros(len(price))
        
        for i in range(M, len(price)):
            # Input vector (past M samples)
            x = price[i-M:i][::-1]
            
            # Predicted output
            y_pred = np.dot(w, x)
            filtered[i] = y_pred
            
            # Desired output (current price)
            d = price[i]
            
            # Error
            e = d - y_pred
            prediction_error[i] = e
            
            # Update weights (LMS algorithm)
            w = w + mu * e * x
        
        filtered_series = pd.Series(filtered, index=data.index)
        error_series = pd.Series(prediction_error, index=data.index)
        
        # Signal: price above adaptive filter
        adaptive_signal = (data['close'] > filtered_series).astype(float)
        
        # Smooth
        adaptive_smooth = adaptive_signal.rolling(5).mean()
        
        # Filter quality (low error = good)
        filter_quality = 1 - abs(error_series).rolling(period).mean() / data['close'].rolling(period).std()
        filter_quality = filter_quality.clip(0, 1)
        
        return pd.DataFrame({
            'filtered': filtered_series,
            'prediction_error': error_series,
            'adaptive_signal': adaptive_signal,
            'adaptive_smooth': adaptive_smooth,
            'filter_quality': filter_quality
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price above adaptive filter
        entries = result['adaptive_smooth'] > 0.6
        
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
            'signal_strength': result['filter_quality']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Above filter
        entries = result['adaptive_signal'] > 0.5
        
        # Exit: Below filter
        exits = result['adaptive_signal'] < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('filter_cross', index=data.index),
            'signal_strength': result['filter_quality']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['adaptive_filtered'] = result['filtered']
        features['adaptive_error'] = result['prediction_error']
        features['adaptive_signal'] = result['adaptive_signal']
        features['adaptive_smooth'] = result['adaptive_smooth']
        features['adaptive_quality'] = result['filter_quality']
        features['adaptive_above_filter'] = (result['adaptive_signal'] > 0.5).astype(int)
        
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

