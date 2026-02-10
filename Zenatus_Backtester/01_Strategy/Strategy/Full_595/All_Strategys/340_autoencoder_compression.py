"""340 - Autoencoder Compression Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AutoencoderCompression:
    """Autoencoder Compression - Compresses price patterns to essential features"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'latent_dim': {'default': 2, 'values': [1,2,3], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AutoencoderCompression", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        latent_dim = params.get('latent_dim', 2)
        
        # Input features (high-dimensional)
        returns = data['close'].pct_change()
        
        input_features = pd.DataFrame({
            'returns': returns,
            'momentum_5': data['close'] - data['close'].shift(5),
            'momentum_10': data['close'] - data['close'].shift(10),
            'volatility': returns.rolling(period).std(),
            'volume': data['volume'],
            'high_low': data['high'] - data['low']
        })
        
        # Normalize
        input_norm = (input_features - input_features.rolling(period).mean()) / (
            input_features.rolling(period).std() + 1e-10
        )
        input_norm = input_norm.fillna(0)
        
        # Encoder: compress to latent space (simplified)
        # Use PCA-like compression
        latent_features = pd.DataFrame(index=data.index)
        reconstruction_quality = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = input_norm.iloc[i-period:i]
            
            if len(window) > 0:
                # Covariance matrix
                cov = window.cov()
                
                try:
                    # Eigendecomposition
                    eigenvalues, eigenvectors = np.linalg.eig(cov)
                    
                    # Sort
                    idx = eigenvalues.argsort()[::-1]
                    eigenvectors = eigenvectors[:, idx]
                    
                    # Encoder: project to latent space
                    current = input_norm.iloc[i].values
                    latent = eigenvectors[:, :latent_dim].T @ current
                    
                    # Decoder: reconstruct
                    reconstructed = eigenvectors[:, :latent_dim] @ latent
                    
                    # Reconstruction error
                    error = np.linalg.norm(current - reconstructed)
                    reconstruction_quality.iloc[i] = 1 / (1 + error)
                    
                    # Store first latent dimension
                    latent_features.loc[data.index[i], 'latent_1'] = latent[0]
                    
                except:
                    latent_features.loc[data.index[i], 'latent_1'] = 0
                    reconstruction_quality.iloc[i] = 0.5
        
        latent_score = latent_features['latent_1'].fillna(0)
        
        # Normalize to probability
        latent_prob = 1 / (1 + np.exp(-2 * latent_score))
        
        # Smooth
        latent_smooth = latent_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'latent_score': latent_score,
            'latent_prob': latent_prob,
            'latent_smooth': latent_smooth,
            'reconstruction_quality': reconstruction_quality
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High latent score
        entries = result['latent_smooth'] > 0.6
        
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
            'signal_strength': result['reconstruction_quality']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['latent_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['latent_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('latent_reversal', index=data.index),
            'signal_strength': result['reconstruction_quality']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ae_latent_score'] = result['latent_score']
        features['ae_latent_prob'] = result['latent_prob']
        features['ae_latent_smooth'] = result['latent_smooth']
        features['ae_reconstruction_quality'] = result['reconstruction_quality']
        features['ae_high_score'] = (result['latent_smooth'] > 0.6).astype(int)
        features['ae_high_quality'] = (result['reconstruction_quality'] > 0.7).astype(int)
        
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

