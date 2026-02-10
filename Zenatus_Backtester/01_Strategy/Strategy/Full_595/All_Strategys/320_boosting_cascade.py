"""320 - Boosting Cascade (AdaBoost-Inspired)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BoostingCascade:
    """Boosting Cascade - Sequential boosting with adaptive weights"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_stages': {'default': 5, 'values': [3,5,7,10], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BoostingCascade", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_stages = params.get('n_stages', 5)
        
        # Target: future returns
        returns = data['close'].pct_change()
        
        # Initialize
        predictions = []
        weights = []
        sample_weights = pd.Series(1.0, index=data.index)
        
        for stage in range(min(n_stages, 5)):
            # Weak learner: simple threshold on weighted data
            # Feature: momentum
            momentum = data['close'] - data['close'].shift(stage + 1)
            
            # Weighted threshold
            threshold = (momentum * sample_weights).rolling(period).median()
            weak_pred = (momentum > threshold).astype(float) - 0.5
            
            # Calculate error
            target = (returns.shift(-1) > 0).astype(float) - 0.5
            error = abs(weak_pred - target)
            
            # Stage weight (lower error = higher weight)
            stage_error = error.rolling(period).mean()
            stage_weight = np.log((1 - stage_error) / (stage_error + 1e-10))
            stage_weight = stage_weight.clip(-3, 3)
            
            predictions.append(weak_pred * stage_weight)
            weights.append(stage_weight)
            
            # Update sample weights (focus on errors)
            sample_weights = sample_weights * np.exp(error)
            sample_weights = sample_weights / sample_weights.rolling(period).sum()
        
        # Combine predictions
        cascade_score = sum(predictions) / len(predictions)
        
        # Normalize to probability
        cascade_prob = 1 / (1 + np.exp(-5 * cascade_score))
        
        # Smooth
        cascade_smooth = cascade_prob.rolling(5).mean()
        
        # Ensemble confidence
        pred_std = pd.concat(predictions, axis=1).std(axis=1)
        confidence = 1 - pred_std
        
        return pd.DataFrame({
            'cascade_score': cascade_score,
            'cascade_prob': cascade_prob,
            'cascade_smooth': cascade_smooth,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High cascade probability
        entries = result['cascade_smooth'] > 0.6
        
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
        
        # Entry: High probability
        entries = result['cascade_smooth'] > 0.6
        
        # Exit: Low probability
        exits = result['cascade_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('cascade_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['boosting_cascade_score'] = result['cascade_score']
        features['boosting_cascade_prob'] = result['cascade_prob']
        features['boosting_cascade_smooth'] = result['cascade_smooth']
        features['boosting_confidence'] = result['confidence']
        features['boosting_high_prob'] = (result['cascade_smooth'] > 0.6).astype(int)
        features['boosting_low_prob'] = (result['cascade_smooth'] < 0.4).astype(int)
        
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

