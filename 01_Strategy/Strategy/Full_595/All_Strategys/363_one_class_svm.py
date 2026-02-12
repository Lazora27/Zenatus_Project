"""363 - One-Class SVM Anomaly"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_OneClassSVM:
    """One-Class SVM - Support Vector Machine for novelty detection"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'nu': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "OneClassSVM", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        nu = params.get('nu', 0.1)  # Expected fraction of outliers
        
        # Features
        returns = data['close'].pct_change().fillna(0)
        
        features = pd.DataFrame({
            'returns': returns,
            'momentum': (data['close'] - data['close'].shift(5)).fillna(0)
        })
        
        # Normalize
        features_norm = (features - features.rolling(period).mean()) / (
            features.rolling(period).std() + 1e-10
        )
        features_norm = features_norm.fillna(0)
        
        # Simplified One-Class SVM (using distance from center)
        svm_scores = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = features_norm.iloc[i-period:i]
            current = features_norm.iloc[i].values
            
            # Center of normal data
            center = window.mean().values
            
            # Distance from center
            distance = np.linalg.norm(current - center)
            
            # Threshold (based on nu percentile)
            distances_window = []
            for j in range(len(window)):
                d = np.linalg.norm(window.iloc[j].values - center)
                distances_window.append(d)
            
            threshold = np.percentile(distances_window, (1-nu)*100)
            
            # Anomaly if beyond threshold
            svm_scores.iloc[i] = distance - threshold
        
        # Positive score = outlier
        is_outlier = (svm_scores > 0).astype(int)
        
        # Outlier with positive momentum
        momentum = data['close'] > data['close'].shift(1)
        outlier_signal = (is_outlier & momentum).astype(float)
        
        # Smooth
        outlier_smooth = outlier_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'svm_score': svm_scores,
            'is_outlier': is_outlier,
            'outlier_signal': outlier_signal,
            'outlier_smooth': outlier_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Outlier detected
        entries = result['outlier_smooth'] > 0.3
        
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
            'signal_strength': result['outlier_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Outlier
        entries = result['is_outlier'] == 1
        
        # Exit: Normal
        exits = result['is_outlier'] == 0
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('svm_normal', index=data.index),
            'signal_strength': result['outlier_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['svm_score'] = result['svm_score']
        features['svm_is_outlier'] = result['is_outlier']
        features['svm_signal'] = result['outlier_signal']
        features['svm_smooth'] = result['outlier_smooth']
        
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

