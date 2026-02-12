"""342 - DBSCAN Anomaly Detection"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DBSCANAnomaly:
    """DBSCAN Anomaly - Density-based anomaly detection"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'eps': {'default': 0.5, 'values': [0.3,0.5,0.7,1.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DBSCANAnomaly", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        eps = params.get('eps', 0.5)
        
        # Features
        returns = data['close'].pct_change()
        volatility = returns.rolling(period).std()
        
        features = pd.DataFrame({
            'returns': returns.fillna(0),
            'volatility': volatility.fillna(0)
        })
        
        # Normalize
        features_norm = (features - features.rolling(period).mean()) / (features.rolling(period).std() + 1e-10)
        features_norm = features_norm.fillna(0)
        
        # Density-based clustering
        is_anomaly = pd.Series(0, index=data.index)
        density_score = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            current = features_norm.iloc[i].values
            window = features_norm.iloc[i-period:i]
            
            # Count neighbors within eps
            neighbors = 0
            distances = []
            
            for j in range(len(window)):
                dist = np.linalg.norm(current - window.iloc[j].values)
                distances.append(dist)
                
                if dist < eps:
                    neighbors += 1
            
            # Density score
            density_score.iloc[i] = neighbors / period
            
            # Anomaly if low density (outlier)
            if density_score.iloc[i] < 0.2:
                is_anomaly.iloc[i] = 1
        
        # Anomaly with positive momentum = opportunity
        price_up = data['close'] > data['close'].shift(1)
        anomaly_signal = is_anomaly & price_up.astype(int)
        
        return pd.DataFrame({
            'density_score': density_score,
            'is_anomaly': is_anomaly,
            'anomaly_signal': anomaly_signal
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly with upward momentum
        entries = result['anomaly_signal'] == 1
        
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
            'signal_strength': (1 - result['density_score'])
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly detected
        entries = result['anomaly_signal'] == 1
        
        # Exit: Return to normal density
        exits = (result['is_anomaly'] == 0) & (result['is_anomaly'].shift(1) == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('density_normalized', index=data.index),
            'signal_strength': (1 - result['density_score'])
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['dbscan_density'] = result['density_score']
        features['dbscan_is_anomaly'] = result['is_anomaly']
        features['dbscan_anomaly_signal'] = result['anomaly_signal']
        features['dbscan_low_density'] = (result['density_score'] < 0.3).astype(int)
        
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

