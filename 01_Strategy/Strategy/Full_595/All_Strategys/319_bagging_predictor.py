"""319 - Bagging Predictor (Bootstrap Aggregating)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BaggingPredictor:
    """Bagging Predictor - Bootstrap aggregating for robust predictions"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_bags': {'default': 10, 'values': [5,10,15,20], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BaggingPredictor", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_bags = params.get('n_bags', 10)
        
        # Create bootstrap samples and predictions
        returns = data['close'].pct_change()
        
        bag_predictions = []
        
        for bag in range(min(n_bags, 10)):
            # Bootstrap sample (with replacement simulation)
            # Use different periods for diversity
            bag_period = period + (bag - n_bags//2)
            bag_period = max(5, min(50, bag_period))
            
            # Simple predictor on bootstrap sample
            sma = data['close'].rolling(bag_period).mean()
            prediction = (data['close'] > sma).astype(float)
            
            bag_predictions.append(prediction)
        
        # Aggregate predictions
        bag_df = pd.concat(bag_predictions, axis=1)
        bagging_score = bag_df.mean(axis=1)
        
        # Variance (uncertainty)
        bagging_variance = bag_df.std(axis=1)
        
        # Confidence (low variance = high confidence)
        confidence = 1 - bagging_variance
        
        # Smooth
        bagging_smooth = bagging_score.rolling(5).mean()
        
        return pd.DataFrame({
            'bagging_score': bagging_score,
            'bagging_smooth': bagging_smooth,
            'bagging_variance': bagging_variance,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High bagging score
        entries = result['bagging_smooth'] > 0.6
        
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
            'signal_strength': result['confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['bagging_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['bagging_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('bagging_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['bagging_score'] = result['bagging_score']
        features['bagging_smooth'] = result['bagging_smooth']
        features['bagging_variance'] = result['bagging_variance']
        features['bagging_confidence'] = result['confidence']
        features['bagging_high_score'] = (result['bagging_smooth'] > 0.6).astype(int)
        features['bagging_low_variance'] = (result['bagging_variance'] < 0.2).astype(int)
        
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

