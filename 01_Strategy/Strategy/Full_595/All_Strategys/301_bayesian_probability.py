"""301 - Bayesian Probability Estimation"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BayesianProbability:
    """Bayesian Probability - Estimates probability of price direction using Bayesian inference"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 0.6, 'values': [0.55,0.6,0.65,0.7,0.75], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BayesianProbability", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate returns
        returns = data['close'].pct_change()
        
        # Prior probability (historical frequency)
        prior_prob_up = (returns > 0).rolling(period).mean()
        
        # Likelihood based on recent momentum
        momentum = data['close'] - data['close'].shift(5)
        likelihood_up = (momentum > 0).astype(float)
        
        # Bayesian update: P(Up|Evidence) = P(Evidence|Up) * P(Up) / P(Evidence)
        evidence = (momentum != 0).astype(float).replace(0, 1)
        posterior_prob_up = (likelihood_up * prior_prob_up) / evidence
        posterior_prob_up = posterior_prob_up.clip(0, 1)
        
        # Smooth posterior
        posterior_smooth = posterior_prob_up.rolling(5).mean()
        
        # Confidence (based on consistency)
        confidence = 1 - returns.rolling(period).std()
        
        return pd.DataFrame({
            'prior_prob_up': prior_prob_up,
            'posterior_prob_up': posterior_prob_up,
            'posterior_smooth': posterior_smooth,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        threshold = params.get('threshold', 0.6)
        
        # Entry: High probability of upward move
        entries = result['posterior_smooth'] > threshold
        
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
            'signal_strength': result['posterior_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        threshold = params.get('threshold', 0.6)
        
        # Entry: High probability
        entries = result['posterior_smooth'] > threshold
        
        # Exit: Low probability
        exits = result['posterior_smooth'] < (1 - threshold)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('prob_reversal', index=data.index),
            'signal_strength': result['posterior_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['prior_prob_up'] = result['prior_prob_up']
        features['posterior_prob_up'] = result['posterior_prob_up']
        features['posterior_smooth'] = result['posterior_smooth']
        features['confidence'] = result['confidence']
        features['high_prob'] = (result['posterior_smooth'] > 0.6).astype(int)
        features['low_prob'] = (result['posterior_smooth'] < 0.4).astype(int)
        features['prob_change'] = result['posterior_smooth'].diff()
        
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

