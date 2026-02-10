"""345 - Spectral Clustering Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SpectralClustering:
    """Spectral Clustering - Graph-based clustering for market states"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_clusters': {'default': 2, 'values': [2,3,4], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SpectralClustering", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_clusters = params.get('n_clusters', 2)
        
        # Features
        returns = data['close'].pct_change().fillna(0)
        
        # Build similarity graph
        spectral_score = pd.Series(0.0, index=data.index)
        cluster_labels = pd.Series(0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i]
            
            # Similarity matrix (correlation-based)
            similarity_matrix = np.zeros((len(window), len(window)))
            
            for j in range(len(window)):
                for k in range(len(window)):
                    if j != k:
                        # Similarity based on return difference
                        diff = abs(window.iloc[j] - window.iloc[k])
                        similarity_matrix[j, k] = np.exp(-diff * 10)
            
            # Degree matrix
            degree = similarity_matrix.sum(axis=1)
            
            # Laplacian matrix
            D = np.diag(degree)
            L = D - similarity_matrix
            
            try:
                # Eigendecomposition
                eigenvalues, eigenvectors = np.linalg.eig(L)
                
                # Sort by eigenvalue
                idx = eigenvalues.argsort()
                eigenvectors = eigenvectors[:, idx]
                
                # Use second smallest eigenvector for clustering
                if len(eigenvectors) > 1:
                    cluster_vec = eigenvectors[:, 1]
                    
                    # Simple threshold clustering
                    threshold = np.median(cluster_vec)
                    clusters = (cluster_vec > threshold).astype(int)
                    
                    # Assign current point to cluster
                    # Use last point in window
                    cluster_labels.iloc[i] = clusters[-1]
                    
                    # Score based on cluster
                    cluster_returns = window[clusters == clusters[-1]]
                    if len(cluster_returns) > 0:
                        spectral_score.iloc[i] = (cluster_returns > 0).mean()
                    else:
                        spectral_score.iloc[i] = 0.5
                        
            except:
                spectral_score.iloc[i] = 0.5
                cluster_labels.iloc[i] = 0
        
        # Smooth
        spectral_smooth = spectral_score.rolling(5).mean()
        
        return pd.DataFrame({
            'spectral_score': spectral_score,
            'spectral_smooth': spectral_smooth,
            'cluster_label': cluster_labels
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High spectral score
        entries = result['spectral_smooth'] > 0.6
        
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
            'signal_strength': result['spectral_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['spectral_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['spectral_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('spectral_reversal', index=data.index),
            'signal_strength': result['spectral_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['spectral_score'] = result['spectral_score']
        features['spectral_smooth'] = result['spectral_smooth']
        features['spectral_cluster'] = result['cluster_label']
        features['spectral_high_score'] = (result['spectral_smooth'] > 0.6).astype(int)
        
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

