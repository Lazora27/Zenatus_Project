"""338 - Manifold Learning Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ManifoldLearning:
    """Manifold Learning - Non-linear dimensionality reduction"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_neighbors': {'default': 5, 'values': [3,5,7,10], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ManifoldLearning", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_neighbors = params.get('n_neighbors', 5)
        
        # Create high-dimensional features
        returns = data['close'].pct_change()
        
        features = []
        for lag in range(1, 6):
            features.append(returns.shift(lag))
        
        features_df = pd.concat(features, axis=1).fillna(0)
        
        # Simplified manifold embedding (local linear embedding concept)
        manifold_embedding = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Current point
            current = features_df.iloc[i].values
            
            # Find nearest neighbors
            window = features_df.iloc[i-period:i]
            
            # Calculate distances
            distances = []
            for j in range(len(window)):
                dist = np.linalg.norm(current - window.iloc[j].values)
                distances.append(dist)
            
            # Get k nearest neighbors
            distances = np.array(distances)
            nearest_idx = np.argsort(distances)[:n_neighbors]
            
            # Reconstruct current point from neighbors
            if len(nearest_idx) > 0:
                neighbors = window.iloc[nearest_idx]
                
                # Simple average of neighbors
                reconstruction = neighbors.mean().values
                
                # Embedding score (reconstruction quality)
                reconstruction_error = np.linalg.norm(current - reconstruction)
                manifold_embedding.iloc[i] = -reconstruction_error
        
        # Normalize
        manifold_norm = (manifold_embedding - manifold_embedding.rolling(period).mean()) / (
            manifold_embedding.rolling(period).std() + 1e-10
        )
        
        manifold_prob = 1 / (1 + np.exp(-2 * manifold_norm))
        
        # Smooth
        manifold_smooth = manifold_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'manifold_embedding': manifold_embedding,
            'manifold_norm': manifold_norm,
            'manifold_prob': manifold_prob,
            'manifold_smooth': manifold_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High manifold score
        entries = result['manifold_smooth'] > 0.6
        
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
            'signal_strength': result['manifold_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['manifold_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['manifold_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('manifold_reversal', index=data.index),
            'signal_strength': result['manifold_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['manifold_embedding'] = result['manifold_embedding']
        features['manifold_norm'] = result['manifold_norm']
        features['manifold_prob'] = result['manifold_prob']
        features['manifold_smooth'] = result['manifold_smooth']
        features['manifold_high_score'] = (result['manifold_smooth'] > 0.6).astype(int)
        
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

