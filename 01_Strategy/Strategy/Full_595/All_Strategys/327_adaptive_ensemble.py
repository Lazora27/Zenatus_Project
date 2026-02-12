"""327 - Adaptive Ensemble System"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AdaptiveEnsemble:
    """Adaptive Ensemble - Dynamically weights ensemble members based on performance"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'adaptation_rate': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AdaptiveEnsemble", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        adapt_rate = params.get('adaptation_rate', 0.1)
        
        # Ensemble members
        returns = data['close'].pct_change()
        
        # Member 1: Trend follower
        sma = data['close'].rolling(period).mean()
        member1 = (data['close'] > sma).astype(float)
        
        # Member 2: Mean reversion
        zscore = (data['close'] - sma) / (data['close'].rolling(period).std() + 1e-10)
        member2 = (zscore < -1).astype(float)
        
        # Member 3: Momentum
        momentum = data['close'] - data['close'].shift(5)
        member3 = (momentum > 0).astype(float)
        
        # Member 4: Volume
        vol_ratio = data['volume'] / data['volume'].rolling(period).mean()
        member4 = (vol_ratio > 1.2).astype(float)
        
        # Track performance of each member
        future_returns = returns.shift(-1)
        
        # Initialize weights
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        
        # Adaptive weighting
        adaptive_pred = pd.Series(0.0, index=data.index)
        weight_history = []
        
        for i in range(period, len(data)):
            # Current predictions
            predictions = np.array([
                member1.iloc[i],
                member2.iloc[i],
                member3.iloc[i],
                member4.iloc[i]
            ])
            
            # Weighted prediction
            adaptive_pred.iloc[i] = np.dot(weights, predictions)
            
            # Update weights based on recent performance
            if i >= period + 10:
                # Calculate recent accuracy for each member
                for j, member in enumerate([member1, member2, member3, member4]):
                    recent_correct = ((member.iloc[i-10:i] > 0.5) == (future_returns.iloc[i-10:i] > 0)).sum()
                    accuracy = recent_correct / 10
                    
                    # Adapt weight
                    weights[j] = weights[j] + adapt_rate * (accuracy - 0.5)
            
            # Normalize weights
            weights = np.clip(weights, 0.1, 0.9)
            weights = weights / weights.sum()
            
            weight_history.append(weights.copy())
        
        # Smooth
        adaptive_smooth = adaptive_pred.rolling(5).mean()
        
        # Weight stability
        if len(weight_history) > 10:
            weight_changes = [np.std(weight_history[i]) for i in range(len(weight_history))]
            weight_stability = pd.Series([1]*period + weight_changes + [1]*(len(data)-period-len(weight_changes)), 
                                        index=data.index)
        else:
            weight_stability = pd.Series(1, index=data.index)
        
        return pd.DataFrame({
            'adaptive_pred': adaptive_pred,
            'adaptive_smooth': adaptive_smooth,
            'weight_stability': weight_stability
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High adaptive prediction
        entries = result['adaptive_smooth'] > 0.6
        
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
            'signal_strength': result['adaptive_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High prediction
        entries = result['adaptive_smooth'] > 0.6
        
        # Exit: Low prediction
        exits = result['adaptive_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('adaptive_reversal', index=data.index),
            'signal_strength': result['adaptive_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['adaptive_pred'] = result['adaptive_pred']
        features['adaptive_smooth'] = result['adaptive_smooth']
        features['adaptive_weight_stability'] = result['weight_stability']
        features['adaptive_high_pred'] = (result['adaptive_smooth'] > 0.6).astype(int)
        features['adaptive_low_pred'] = (result['adaptive_smooth'] < 0.4).astype(int)
        
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

