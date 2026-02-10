"""348 - Kalman Filter Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_KalmanFilter:
    """Kalman Filter - Optimal state estimation and noise filtering"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'process_noise': {'default': 0.01, 'values': [0.001,0.01,0.1], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "KalmanFilter", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        Q = params.get('process_noise', 0.01)  # Process noise
        
        # Simplified 1D Kalman Filter
        # State: price level and velocity
        
        # Initialize
        x_est = data['close'].iloc[0]  # State estimate
        P_est = 1.0  # Estimate covariance
        
        kalman_estimates = []
        kalman_velocity = []
        kalman_confidence = []
        
        for i in range(len(data)):
            # Measurement
            z = data['close'].iloc[i]
            
            # Measurement noise (from recent volatility)
            if i >= period:
                R = data['close'].iloc[i-period:i].std() ** 2
            else:
                R = 1.0
            
            # Prediction step
            x_pred = x_est
            P_pred = P_est + Q
            
            # Update step
            # Kalman gain
            K = P_pred / (P_pred + R)
            
            # Update estimate
            x_est = x_pred + K * (z - x_pred)
            P_est = (1 - K) * P_pred
            
            kalman_estimates.append(x_est)
            
            # Velocity (trend)
            if i > 0:
                velocity = x_est - kalman_estimates[-2] if len(kalman_estimates) > 1 else 0
            else:
                velocity = 0
            
            kalman_velocity.append(velocity)
            
            # Confidence (inverse of covariance)
            confidence = 1 / (1 + P_est)
            kalman_confidence.append(confidence)
        
        kalman_series = pd.Series(kalman_estimates, index=data.index)
        velocity_series = pd.Series(kalman_velocity, index=data.index)
        confidence_series = pd.Series(kalman_confidence, index=data.index)
        
        # Signal: price above Kalman estimate with positive velocity
        signal = ((data['close'] > kalman_series) & (velocity_series > 0)).astype(float)
        
        # Smooth
        signal_smooth = signal.rolling(5).mean()
        
        return pd.DataFrame({
            'kalman_estimate': kalman_series,
            'kalman_velocity': velocity_series,
            'kalman_confidence': confidence_series,
            'signal_smooth': signal_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price above Kalman with positive velocity
        entries = result['signal_smooth'] > 0.6
        
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
            'signal_strength': result['kalman_confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive signal
        entries = result['signal_smooth'] > 0.6
        
        # Exit: Negative signal
        exits = result['signal_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('kalman_reversal', index=data.index),
            'signal_strength': result['kalman_confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['kalman_estimate'] = result['kalman_estimate']
        features['kalman_velocity'] = result['kalman_velocity']
        features['kalman_confidence'] = result['kalman_confidence']
        features['kalman_signal'] = result['signal_smooth']
        features['kalman_positive'] = (result['signal_smooth'] > 0.6).astype(int)
        features['kalman_high_confidence'] = (result['kalman_confidence'] > 0.7).astype(int)
        
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

