"""318 - Stacking Ensemble Meta-Learner"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_StackingEnsemble:
    """Stacking Ensemble - Meta-learner combines base predictions"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "StackingEnsemble", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Base learner 1: Trend predictor
        sma = data['close'].rolling(period).mean()
        trend_pred = ((data['close'] - sma) / sma).fillna(0)
        
        # Base learner 2: Momentum predictor
        momentum = data['close'] - data['close'].shift(5)
        momentum_pred = (momentum / data['close'].shift(5)).fillna(0)
        
        # Base learner 3: Volatility predictor
        returns = data['close'].pct_change()
        volatility = returns.rolling(period).std()
        vol_pred = (volatility - volatility.rolling(period).mean()) / (volatility.rolling(period).std() + 1e-10)
        vol_pred = vol_pred.fillna(0)
        
        # Base learner 4: Volume predictor
        vol_ratio = data['volume'] / data['volume'].rolling(period).mean()
        vol_ratio_pred = (vol_ratio - 1).fillna(0)
        
        # Meta-learner: weighted combination
        # Weights learned from historical performance (simplified)
        weights = [0.3, 0.3, 0.2, 0.2]
        
        meta_prediction = (
            weights[0] * trend_pred +
            weights[1] * momentum_pred +
            weights[2] * vol_pred +
            weights[3] * vol_ratio_pred
        )
        
        # Normalize to probability
        meta_prob = 1 / (1 + np.exp(-5 * meta_prediction))
        
        # Smooth
        meta_smooth = meta_prob.rolling(5).mean()
        
        # Confidence (agreement between base learners)
        base_preds = pd.DataFrame({
            'trend': trend_pred,
            'momentum': momentum_pred,
            'vol': vol_pred,
            'volume': vol_ratio_pred
        })
        
        confidence = 1 - base_preds.std(axis=1)
        
        return pd.DataFrame({
            'meta_prediction': meta_prediction,
            'meta_prob': meta_prob,
            'meta_smooth': meta_smooth,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High meta prediction
        entries = result['meta_smooth'] > 0.6
        
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
        
        # Entry: High prediction
        entries = result['meta_smooth'] > 0.6
        
        # Exit: Low prediction
        exits = result['meta_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('meta_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['stacking_meta_pred'] = result['meta_prediction']
        features['stacking_meta_prob'] = result['meta_prob']
        features['stacking_meta_smooth'] = result['meta_smooth']
        features['stacking_confidence'] = result['confidence']
        features['stacking_high_pred'] = (result['meta_smooth'] > 0.6).astype(int)
        features['stacking_low_pred'] = (result['meta_smooth'] < 0.4).astype(int)
        
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

