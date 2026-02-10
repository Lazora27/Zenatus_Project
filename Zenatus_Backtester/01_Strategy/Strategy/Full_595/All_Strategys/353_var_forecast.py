"""353 - VAR (Vector Autoregression) Forecast"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VARForecast:
    """VAR Forecast - Multivariate time series forecasting"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'lag_order': {'default': 2, 'values': [1,2,3], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VARForecast", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        lag = params.get('lag_order', 2)
        
        # Multiple time series
        returns = data['close'].pct_change().fillna(0)
        vol_change = data['volume'].pct_change().fillna(0)
        
        # VAR model: each variable depends on lags of all variables
        var_forecast = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Historical data
            returns_hist = returns.iloc[i-period:i]
            vol_hist = vol_change.iloc[i-period:i]
            
            # Simplified VAR: use correlation structure
            if lag == 1:
                # Returns forecast
                phi_rr = returns_hist.autocorr(lag=1)
                phi_rv = returns_hist.corr(vol_hist.shift(1))
                
                if not np.isnan(phi_rr) and not np.isnan(phi_rv):
                    var_forecast.iloc[i] = (phi_rr * returns.iloc[i-1] + 
                                           phi_rv * vol_change.iloc[i-1])
            else:
                # VAR(2)
                phi_rr1 = returns_hist.autocorr(lag=1)
                phi_rr2 = returns_hist.autocorr(lag=2)
                
                if not np.isnan(phi_rr1) and not np.isnan(phi_rr2):
                    var_forecast.iloc[i] = (phi_rr1 * returns.iloc[i-1] + 
                                           phi_rr2 * returns.iloc[i-2])
        
        # Forecast signal
        forecast_signal = (var_forecast > 0).astype(float)
        
        # Smooth
        forecast_smooth = forecast_signal.rolling(5).mean()
        
        # Forecast accuracy
        actual_returns = returns
        forecast_error = abs(actual_returns - var_forecast)
        accuracy = 1 - forecast_error.rolling(period).mean()
        accuracy = accuracy.clip(0, 1)
        
        return pd.DataFrame({
            'var_forecast': var_forecast,
            'forecast_signal': forecast_signal,
            'forecast_smooth': forecast_smooth,
            'accuracy': accuracy
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive VAR forecast
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
        
        # Entry: Positive forecast
        entries = result['forecast_smooth'] > 0.6
        
        # Exit: Negative forecast
        exits = result['forecast_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('var_reversal', index=data.index),
            'signal_strength': result['accuracy']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['var_forecast'] = result['var_forecast']
        features['var_signal'] = result['forecast_signal']
        features['var_smooth'] = result['forecast_smooth']
        features['var_accuracy'] = result['accuracy']
        features['var_positive'] = (result['forecast_smooth'] > 0.6).astype(int)
        
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

