"""322 - Meta-Learning Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MetaLearning:
    """Meta-Learning - Learns from multiple market regimes"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_regimes': {'default': 3, 'values': [2,3,4,5], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MetaLearning", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_regimes = params.get('n_regimes', 3)
        
        # Identify market regimes
        returns = data['close'].pct_change()
        volatility = returns.rolling(period).std()
        
        # Regime 1: Low volatility (ranging)
        # Regime 2: Medium volatility (trending)
        # Regime 3: High volatility (breakout)
        
        vol_percentile = volatility.rolling(100).apply(
            lambda x: pd.Series(x).rank().iloc[-1] / len(x) if len(x) > 0 else 0.5
        ).fillna(0.5)
        
        regime = pd.Series(0, index=data.index)
        if n_regimes == 2:
            regime[vol_percentile > 0.5] = 1
        elif n_regimes == 3:
            regime[vol_percentile > 0.33] = 1
            regime[vol_percentile > 0.67] = 2
        else:
            for i in range(n_regimes):
                regime[vol_percentile > i/n_regimes] = i
        
        # Meta-learner: different strategy per regime
        meta_predictions = []
        
        for reg in range(n_regimes):
            # Strategy for each regime
            if reg == 0:  # Low vol: mean reversion
                sma = data['close'].rolling(period).mean()
                pred = (data['close'] < sma).astype(float)
            elif reg == 1:  # Medium vol: trend following
                sma = data['close'].rolling(period).mean()
                pred = (data['close'] > sma).astype(float)
            else:  # High vol: momentum
                momentum = data['close'] - data['close'].shift(5)
                pred = (momentum > 0).astype(float)
            
            # Apply only when in regime
            pred_masked = pred.where(regime == reg, 0.5)
            meta_predictions.append(pred_masked)
        
        # Combine predictions
        meta_score = pd.concat(meta_predictions, axis=1).mean(axis=1)
        
        # Smooth
        meta_smooth = meta_score.rolling(5).mean()
        
        # Regime confidence
        regime_stability = (regime == regime.shift(1)).rolling(10).mean()
        
        return pd.DataFrame({
            'regime': regime,
            'meta_score': meta_score,
            'meta_smooth': meta_smooth,
            'regime_stability': regime_stability,
            'volatility': volatility
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High meta score
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
            'signal_strength': result['regime_stability']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['meta_smooth'] > 0.6
        
        # Exit: Low score or regime change
        exits = (result['meta_smooth'] < 0.4) | (result['regime'].diff() != 0)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('meta_reversal', index=data.index),
            'signal_strength': result['regime_stability']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['meta_regime'] = result['regime']
        features['meta_score'] = result['meta_score']
        features['meta_smooth'] = result['meta_smooth']
        features['meta_regime_stability'] = result['regime_stability']
        features['meta_volatility'] = result['volatility']
        features['meta_high_score'] = (result['meta_smooth'] > 0.6).astype(int)
        features['meta_regime_change'] = (result['regime'].diff() != 0).astype(int)
        
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

