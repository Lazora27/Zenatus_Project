"""346 - ARIMA Forecast Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ARIMAForecast:
    """ARIMA Forecast - Autoregressive Integrated Moving Average"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'ar_order': {'default': 2, 'values': [1,2,3], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ARIMAForecast", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        ar_order = params.get('ar_order', 2)
        
        # Returns (integrated)
        returns = data['close'].pct_change().fillna(0)
        
        # AR component
        ar_forecast = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i]
            
            # Simple AR model
            if ar_order == 1:
                # AR(1): y_t = phi * y_{t-1}
                phi = window.autocorr(lag=1)
                if not np.isnan(phi):
                    ar_forecast.iloc[i] = phi * returns.iloc[i-1]
                    
            elif ar_order == 2:
                # AR(2): y_t = phi1 * y_{t-1} + phi2 * y_{t-2}
                phi1 = window.autocorr(lag=1)
                phi2 = window.autocorr(lag=2)
                
                if not np.isnan(phi1) and not np.isnan(phi2):
                    ar_forecast.iloc[i] = phi1 * returns.iloc[i-1] + phi2 * returns.iloc[i-2]
            else:
                # AR(3)
                phi1 = window.autocorr(lag=1)
                phi2 = window.autocorr(lag=2)
                phi3 = window.autocorr(lag=3)
                
                if not np.isnan(phi1) and not np.isnan(phi2) and not np.isnan(phi3):
                    ar_forecast.iloc[i] = (phi1 * returns.iloc[i-1] + 
                                          phi2 * returns.iloc[i-2] + 
                                          phi3 * returns.iloc[i-3])
        
        # MA component (moving average of errors)
        actual_returns = returns
        forecast_error = actual_returns - ar_forecast
        ma_component = forecast_error.rolling(5).mean()
        
        # ARIMA forecast
        arima_forecast = ar_forecast + ma_component
        
        # Forecast signal
        forecast_signal = (arima_forecast > 0).astype(float)
        
        # Smooth
        forecast_smooth = forecast_signal.rolling(5).mean()
        
        # Forecast confidence
        forecast_confidence = 1 - abs(forecast_error).rolling(period).mean()
        
        return pd.DataFrame({
            'arima_forecast': arima_forecast,
            'forecast_signal': forecast_signal,
            'forecast_smooth': forecast_smooth,
            'forecast_confidence': forecast_confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive forecast
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
            'signal_strength': result['forecast_confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive forecast
        entries = result['forecast_smooth'] > 0.6
        
        # Exit: Negative forecast
        exits = result['forecast_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('forecast_reversal', index=data.index),
            'signal_strength': result['forecast_confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['arima_forecast'] = result['arima_forecast']
        features['arima_signal'] = result['forecast_signal']
        features['arima_smooth'] = result['forecast_smooth']
        features['arima_confidence'] = result['forecast_confidence']
        features['arima_positive'] = (result['forecast_smooth'] > 0.6).astype(int)
        
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

