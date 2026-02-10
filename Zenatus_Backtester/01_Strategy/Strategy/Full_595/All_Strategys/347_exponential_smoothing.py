"""347 - Exponential Smoothing Forecast"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ExponentialSmoothing:
    """Exponential Smoothing - Triple exponential smoothing (Holt-Winters)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'alpha': {'default': 0.3, 'values': [0.1,0.2,0.3,0.4,0.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ExponentialSmoothing", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        alpha = params.get('alpha', 0.3)
        beta = alpha * 0.5  # Trend smoothing
        gamma = alpha * 0.3  # Seasonal smoothing
        
        # Simple exponential smoothing
        level = data['close'].ewm(alpha=alpha, adjust=False).mean()
        
        # Double exponential (Holt's)
        trend = (data['close'] - data['close'].shift(1)).ewm(alpha=beta, adjust=False).mean()
        
        # Forecast
        forecast = level + trend
        
        # Forecast error
        forecast_error = data['close'] - forecast.shift(1)
        
        # Forecast signal
        forecast_direction = (forecast > data['close']).astype(float)
        
        # Smooth
        forecast_smooth = forecast_direction.rolling(5).mean()
        
        # Forecast accuracy
        accuracy = 1 - abs(forecast_error).rolling(period).mean() / data['close'].rolling(period).std()
        accuracy = accuracy.clip(0, 1)
        
        return pd.DataFrame({
            'level': level,
            'trend': trend,
            'forecast': forecast,
            'forecast_smooth': forecast_smooth,
            'accuracy': accuracy
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Forecast predicts upward movement
        entries = result['forecast_smooth'] > 0.6
        
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
            'signal_strength': result['accuracy']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Upward forecast
        entries = result['forecast_smooth'] > 0.6
        
        # Exit: Downward forecast
        exits = result['forecast_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('forecast_reversal', index=data.index),
            'signal_strength': result['accuracy']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['es_level'] = result['level']
        features['es_trend'] = result['trend']
        features['es_forecast'] = result['forecast']
        features['es_smooth'] = result['forecast_smooth']
        features['es_accuracy'] = result['accuracy']
        features['es_upward_forecast'] = (result['forecast_smooth'] > 0.6).astype(int)
        
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

