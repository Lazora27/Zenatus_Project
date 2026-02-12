"""364 - Elliptic Envelope Anomaly"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_EllipticEnvelope:
    """Elliptic Envelope - Gaussian distribution-based anomaly detection"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'contamination': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "EllipticEnvelope", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        contamination = params.get('contamination', 0.1)
        
        # Features
        returns = data['close'].pct_change().fillna(0)
        volatility = returns.rolling(period).std().fillna(0)
        
        features = pd.DataFrame({
            'returns': returns,
            'volatility': volatility
        })
        
        # Mahalanobis distance (elliptic envelope)
        mahal_distances = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = features.iloc[i-period:i]
            current = features.iloc[i].values
            
            # Mean and covariance
            mean = window.mean().values
            cov = window.cov().values
            
            try:
                # Inverse covariance
                cov_inv = np.linalg.inv(cov + np.eye(len(cov)) * 1e-6)
                
                # Mahalanobis distance
                diff = current - mean
                mahal = np.sqrt(diff @ cov_inv @ diff.T)
                mahal_distances.iloc[i] = mahal
                
            except:
                mahal_distances.iloc[i] = 0
        
        # Threshold based on contamination
        threshold = mahal_distances.rolling(period).quantile(1 - contamination)
        
        # Anomaly if distance > threshold
        is_anomaly = (mahal_distances > threshold).astype(int)
        
        # Anomaly with positive momentum
        momentum = data['close'] > data['close'].shift(1)
        anomaly_signal = (is_anomaly & momentum).astype(float)
        
        # Smooth
        anomaly_smooth = anomaly_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'mahal_distance': mahal_distances,
            'threshold': threshold,
            'is_anomaly': is_anomaly,
            'anomaly_signal': anomaly_signal,
            'anomaly_smooth': anomaly_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly detected
        entries = result['anomaly_smooth'] > 0.3
        
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
            'signal_strength': result['anomaly_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly
        entries = result['is_anomaly'] == 1
        
        # Exit: Normal
        exits = (result['is_anomaly'] == 0) & (result['is_anomaly'].shift(1) == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('envelope_normal', index=data.index),
            'signal_strength': result['anomaly_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['elliptic_mahal'] = result['mahal_distance']
        features['elliptic_threshold'] = result['threshold']
        features['elliptic_is_anomaly'] = result['is_anomaly']
        features['elliptic_signal'] = result['anomaly_signal']
        features['elliptic_smooth'] = result['anomaly_smooth']
        
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

