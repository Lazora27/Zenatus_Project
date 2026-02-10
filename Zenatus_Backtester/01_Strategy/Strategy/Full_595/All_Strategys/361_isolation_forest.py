"""361 - Isolation Forest Anomaly"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_IsolationForest:
    """Isolation Forest - Tree-based anomaly detection"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_trees': {'default': 10, 'values': [5,10,15,20], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "IsolationForest", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_trees = params.get('n_trees', 10)
        
        # Features for anomaly detection
        returns = data['close'].pct_change().fillna(0)
        volatility = returns.rolling(period).std().fillna(0)
        volume_ratio = (data['volume'] / data['volume'].rolling(period).mean()).fillna(1)
        
        features = pd.DataFrame({
            'returns': returns,
            'volatility': volatility,
            'volume_ratio': volume_ratio
        })
        
        # Simplified Isolation Forest
        # Anomaly score based on path length in random trees
        anomaly_scores = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = features.iloc[i-period:i]
            current = features.iloc[i]
            
            # Build multiple random trees
            path_lengths = []
            
            for tree in range(n_trees):
                # Random feature and split
                feature_idx = np.random.randint(0, len(features.columns))
                feature_name = features.columns[feature_idx]
                
                # Random split value
                split_value = window[feature_name].median()
                
                # Path length (how many splits to isolate point)
                path_length = 0
                
                # Simple binary tree depth
                if current[feature_name] < split_value:
                    path_length = 1
                else:
                    path_length = 2
                
                path_lengths.append(path_length)
            
            # Average path length (shorter = more anomalous)
            avg_path_length = np.mean(path_lengths)
            
            # Anomaly score (inverse of path length)
            anomaly_scores.iloc[i] = 1 / (avg_path_length + 1)
        
        # Normalize
        anomaly_norm = (anomaly_scores - anomaly_scores.rolling(period).mean()) / (
            anomaly_scores.rolling(period).std() + 1e-10
        )
        
        # High score = anomaly
        is_anomaly = (anomaly_norm > 1).astype(int)
        
        # Anomaly with positive momentum = opportunity
        momentum = data['close'] > data['close'].shift(1)
        anomaly_signal = (is_anomaly & momentum).astype(float)
        
        # Smooth
        anomaly_smooth = anomaly_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'anomaly_score': anomaly_scores,
            'anomaly_norm': anomaly_norm,
            'is_anomaly': is_anomaly,
            'anomaly_signal': anomaly_signal,
            'anomaly_smooth': anomaly_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly with positive momentum
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
        
        # Entry: Anomaly detected
        entries = result['is_anomaly'] == 1
        
        # Exit: Return to normal
        exits = (result['is_anomaly'] == 0) & (result['is_anomaly'].shift(1) == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('anomaly_resolved', index=data.index),
            'signal_strength': result['anomaly_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['iforest_score'] = result['anomaly_score']
        features['iforest_norm'] = result['anomaly_norm']
        features['iforest_is_anomaly'] = result['is_anomaly']
        features['iforest_signal'] = result['anomaly_signal']
        features['iforest_smooth'] = result['anomaly_smooth']
        
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

