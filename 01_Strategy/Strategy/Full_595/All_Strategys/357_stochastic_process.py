"""357 - Stochastic Process Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_StochasticProcess:
    """Stochastic Process - Geometric Brownian Motion analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "StochasticProcess", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Geometric Brownian Motion: dS = mu*S*dt + sigma*S*dW
        returns = data['close'].pct_change().fillna(0)
        
        # Estimate drift (mu)
        drift = returns.rolling(period).mean()
        
        # Estimate volatility (sigma)
        volatility = returns.rolling(period).std()
        
        # Sharpe-like ratio
        sharpe = drift / (volatility + 1e-10)
        
        # Forecast using GBM
        # E[S_t+1] = S_t * exp(mu * dt)
        dt = 1  # 1 period ahead
        forecast = data['close'] * np.exp(drift * dt)
        
        # Forecast signal
        forecast_signal = (forecast > data['close']).astype(float)
        
        # Smooth
        forecast_smooth = forecast_signal.rolling(5).mean()
        
        # Process confidence (high Sharpe = good signal)
        confidence = (sharpe - sharpe.rolling(50).min()) / (sharpe.rolling(50).max() - sharpe.rolling(50).min() + 1e-10)
        confidence = confidence.clip(0, 1)
        
        return pd.DataFrame({
            'drift': drift,
            'volatility': volatility,
            'sharpe': sharpe,
            'forecast': forecast,
            'forecast_smooth': forecast_smooth,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive drift with good Sharpe
        entries = (result['forecast_smooth'] > 0.6) & (result['sharpe'] > 0)
        
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
            'signal_strength': result['confidence']
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
            'exit_reason': pd.Series('drift_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['gbm_drift'] = result['drift']
        features['gbm_volatility'] = result['volatility']
        features['gbm_sharpe'] = result['sharpe']
        features['gbm_forecast'] = result['forecast']
        features['gbm_smooth'] = result['forecast_smooth']
        features['gbm_confidence'] = result['confidence']
        features['gbm_positive_drift'] = (result['drift'] > 0).astype(int)
        
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

