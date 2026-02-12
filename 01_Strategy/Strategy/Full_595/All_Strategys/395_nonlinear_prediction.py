"""395 - Nonlinear Prediction"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_NonlinearPrediction:
    """Nonlinear Prediction - Local linear prediction in phase space"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'embedding_dim': {'default': 3, 'values': [2,3,4], 'optimize': False},
        'n_neighbors': {'default': 5, 'values': [3,5,7], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "NonlinearPrediction", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        m = params.get('embedding_dim', 3)
        k = params.get('n_neighbors', 5)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Nonlinear prediction
        prediction = pd.Series(0.0, index=data.index)
        prediction_error = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data) - 1):
            window = returns.iloc[i-period:i].values
            
            # Time-delay embedding
            delay = 1
            embedded = []
            targets = []
            
            for j in range(len(window) - (m - 1) * delay - 1):
                vector = [window[j + k_idx * delay] for k_idx in range(m)]
                embedded.append(vector)
                targets.append(window[j + m * delay])
            
            embedded = np.array(embedded)
            targets = np.array(targets)
            
            if len(embedded) > k:
                # Current state
                current_state = embedded[-1]
                
                # Find k nearest neighbors
                distances = []
                for j in range(len(embedded) - 1):
                    dist = np.linalg.norm(current_state - embedded[j])
                    distances.append((dist, j))
                
                distances.sort()
                nearest_k = distances[:k]
                
                # Predict using weighted average of neighbors' futures
                weights = []
                neighbor_targets = []
                
                for dist, idx in nearest_k:
                    weight = 1 / (dist + 1e-10)
                    weights.append(weight)
                    neighbor_targets.append(targets[idx])
                
                weights = np.array(weights)
                weights = weights / weights.sum()
                
                # Weighted prediction
                pred = np.dot(weights, neighbor_targets)
                prediction.iloc[i] = pred
                
                # Actual future value
                actual = returns.iloc[i + 1]
                prediction_error.iloc[i] = abs(actual - pred)
        
        # Prediction quality
        error_normalized = prediction_error / (prediction_error.rolling(period).mean() + 1e-10)
        prediction_quality = 1 / (1 + error_normalized)
        
        # Signal: good prediction quality
        quality_signal = prediction_quality
        
        # Smooth
        quality_smooth = quality_signal.rolling(5).mean()
        
        # Direction signal
        direction_signal = (prediction > 0).astype(float)
        
        return pd.DataFrame({
            'prediction': prediction,
            'prediction_error': prediction_error,
            'prediction_quality': prediction_quality,
            'quality_signal': quality_signal,
            'quality_smooth': quality_smooth,
            'direction_signal': direction_signal
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Good prediction + positive direction
        entries = (result['quality_smooth'] > 0.6) & (result['direction_signal'] > 0.5)
        
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
            'signal_strength': result['quality_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive prediction
        entries = result['prediction'] > 0
        
        # Exit: Negative prediction
        exits = result['prediction'] < 0
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('prediction_reversal', index=data.index),
            'signal_strength': result['quality_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['nonlinear_prediction'] = result['prediction']
        features['nonlinear_error'] = result['prediction_error']
        features['nonlinear_quality'] = result['prediction_quality']
        features['nonlinear_quality_signal'] = result['quality_signal']
        features['nonlinear_quality_smooth'] = result['quality_smooth']
        features['nonlinear_direction'] = result['direction_signal']
        features['nonlinear_positive_pred'] = (result['prediction'] > 0).astype(int)
        
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

