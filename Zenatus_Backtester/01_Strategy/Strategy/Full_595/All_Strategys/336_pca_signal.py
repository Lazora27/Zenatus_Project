"""336 - PCA Signal Extractor"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PCASignal:
    """PCA Signal - Principal Component Analysis for signal extraction"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_components': {'default': 3, 'values': [2,3,4,5], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PCASignal", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_comp = params.get('n_components', 3)
        
        # Create feature matrix
        returns = data['close'].pct_change()
        
        features = pd.DataFrame({
            'returns': returns,
            'momentum_5': data['close'] - data['close'].shift(5),
            'momentum_10': data['close'] - data['close'].shift(10),
            'volatility': returns.rolling(period).std(),
            'volume_ratio': data['volume'] / data['volume'].rolling(period).mean()
        })
        
        # Normalize features
        features_norm = (features - features.rolling(period).mean()) / (features.rolling(period).std() + 1e-10)
        features_norm = features_norm.fillna(0)
        
        # Simplified PCA (using correlation matrix)
        pca_scores = pd.Series(0.0, index=data.index)
        explained_variance = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = features_norm.iloc[i-period:i]
            
            if len(window) > 0:
                # Covariance matrix
                cov_matrix = window.cov()
                
                # Eigenvalues and eigenvectors
                try:
                    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
                    
                    # Sort by eigenvalue
                    idx = eigenvalues.argsort()[::-1]
                    eigenvalues = eigenvalues[idx]
                    eigenvectors = eigenvectors[:, idx]
                    
                    # First principal component
                    pc1 = eigenvectors[:, 0]
                    
                    # Project current data onto PC1
                    current_features = features_norm.iloc[i].values
                    pca_scores.iloc[i] = np.dot(current_features, pc1)
                    
                    # Explained variance
                    explained_variance.iloc[i] = eigenvalues[0] / eigenvalues.sum()
                    
                except:
                    pca_scores.iloc[i] = 0
                    explained_variance.iloc[i] = 0
        
        # Normalize to probability
        pca_prob = 1 / (1 + np.exp(-2 * pca_scores))
        
        # Smooth
        pca_smooth = pca_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'pca_score': pca_scores,
            'pca_prob': pca_prob,
            'pca_smooth': pca_smooth,
            'explained_variance': explained_variance
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High PCA score
        entries = result['pca_smooth'] > 0.6
        
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
            'signal_strength': result['explained_variance']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['pca_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['pca_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pca_reversal', index=data.index),
            'signal_strength': result['explained_variance']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['pca_score'] = result['pca_score']
        features['pca_prob'] = result['pca_prob']
        features['pca_smooth'] = result['pca_smooth']
        features['pca_explained_var'] = result['explained_variance']
        features['pca_high_score'] = (result['pca_smooth'] > 0.6).astype(int)
        features['pca_high_variance'] = (result['explained_variance'] > 0.5).astype(int)
        
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

