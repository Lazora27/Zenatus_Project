"""393 - Phase Space Reconstruction"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PhaseSpaceReconstruction:
    """Phase Space Reconstruction - Reconstructs system dynamics"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'embedding_dim': {'default': 3, 'values': [2,3,4], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PhaseSpaceReconstruction", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        m = params.get('embedding_dim', 3)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Phase space analysis
        trajectory_length = pd.Series(0.0, index=data.index)
        trajectory_curvature = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i].values
            
            # Time-delay embedding
            delay = 1
            embedded = []
            
            for j in range(len(window) - (m - 1) * delay):
                vector = [window[j + k * delay] for k in range(m)]
                embedded.append(vector)
            
            embedded = np.array(embedded)
            
            if len(embedded) > 2:
                # Trajectory length (total distance traveled)
                length = 0
                for j in range(len(embedded) - 1):
                    dist = np.linalg.norm(embedded[j + 1] - embedded[j])
                    length += dist
                
                trajectory_length.iloc[i] = length
                
                # Trajectory curvature (change in direction)
                curvatures = []
                for j in range(1, len(embedded) - 1):
                    # Vectors
                    v1 = embedded[j] - embedded[j - 1]
                    v2 = embedded[j + 1] - embedded[j]
                    
                    # Angle between vectors
                    if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                        cos_angle = np.clip(cos_angle, -1, 1)
                        angle = np.arccos(cos_angle)
                        curvatures.append(angle)
                
                if len(curvatures) > 0:
                    trajectory_curvature.iloc[i] = np.mean(curvatures)
        
        # Normalize
        length_normalized = trajectory_length / (trajectory_length.rolling(50).max() + 1e-10)
        curvature_normalized = trajectory_curvature / (np.pi + 1e-10)
        
        # Low curvature = smooth trajectory = predictable
        smoothness = 1 - curvature_normalized
        
        # Smooth
        smoothness_smooth = smoothness.rolling(5).mean()
        
        return pd.DataFrame({
            'trajectory_length': trajectory_length,
            'trajectory_curvature': trajectory_curvature,
            'length_normalized': length_normalized,
            'smoothness': smoothness,
            'smoothness_smooth': smoothness_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Smooth trajectory
        entries = result['smoothness_smooth'] > 0.6
        
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
            'signal_strength': result['smoothness_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Smooth
        entries = result['smoothness'] > 0.6
        
        # Exit: Erratic
        exits = result['smoothness'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('trajectory_erratic', index=data.index),
            'signal_strength': result['smoothness_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['phase_trajectory_length'] = result['trajectory_length']
        features['phase_trajectory_curvature'] = result['trajectory_curvature']
        features['phase_length_normalized'] = result['length_normalized']
        features['phase_smoothness'] = result['smoothness']
        features['phase_smoothness_smooth'] = result['smoothness_smooth']
        features['phase_smooth_trajectory'] = (result['smoothness'] > 0.6).astype(int)
        
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

