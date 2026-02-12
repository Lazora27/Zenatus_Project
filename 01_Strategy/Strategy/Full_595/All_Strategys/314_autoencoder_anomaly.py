"""314 - Autoencoder Anomaly Detection"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AutoencoderAnomaly:
    """Autoencoder Anomaly - Detects anomalous price patterns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 2.0, 'values': [1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AutoencoderAnomaly", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 2.0)
        
        # Normalize features
        returns = data['close'].pct_change()
        
        # Encoder: Compress to lower dimension
        # Feature 1: Price momentum
        momentum = data['close'] - data['close'].shift(5)
        momentum_norm = (momentum - momentum.rolling(period).mean()) / (momentum.rolling(period).std() + 1e-10)
        
        # Feature 2: Volatility
        volatility = returns.rolling(period).std()
        vol_norm = (volatility - volatility.rolling(period).mean()) / (volatility.rolling(period).std() + 1e-10)
        
        # Feature 3: Volume
        vol_ratio = data['volume'] / data['volume'].rolling(period).mean()
        vol_ratio_norm = (vol_ratio - vol_ratio.rolling(period).mean()) / (vol_ratio.rolling(period).std() + 1e-10)
        
        # Latent representation (compressed)
        latent = (momentum_norm + vol_norm + vol_ratio_norm) / 3
        
        # Decoder: Reconstruct original
        reconstructed = latent  # Simplified
        
        # Reconstruction error
        original = momentum_norm  # Use momentum as target
        reconstruction_error = abs(original - reconstructed)
        
        # Anomaly score
        error_ma = reconstruction_error.rolling(period).mean()
        error_std = reconstruction_error.rolling(period).std()
        anomaly_score = (reconstruction_error - error_ma) / (error_std + 1e-10)
        
        # Anomaly detection
        is_anomaly = abs(anomaly_score) > threshold
        
        return pd.DataFrame({
            'latent': latent,
            'reconstruction_error': reconstruction_error,
            'anomaly_score': anomaly_score,
            'is_anomaly': is_anomaly.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly detected with positive momentum
        price_up = data['close'] > data['close'].shift(1)
        entries = (result['is_anomaly'] == 1) & price_up
        
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
            'signal_strength': abs(result['anomaly_score']).clip(0, 3) / 3
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly detected
        entries = result['is_anomaly'] == 1
        
        # Exit: Return to normal
        exits = (result['is_anomaly'] == 0) & (result['is_anomaly'].shift(1) == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('anomaly_resolved', index=data.index),
            'signal_strength': abs(result['anomaly_score']).clip(0, 3) / 3
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ae_latent'] = result['latent']
        features['ae_reconstruction_error'] = result['reconstruction_error']
        features['ae_anomaly_score'] = result['anomaly_score']
        features['ae_is_anomaly'] = result['is_anomaly']
        features['ae_high_error'] = (result['reconstruction_error'] > result['reconstruction_error'].rolling(50).mean()).astype(int)
        
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

