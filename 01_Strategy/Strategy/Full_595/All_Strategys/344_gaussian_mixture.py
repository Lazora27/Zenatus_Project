"""344 - Gaussian Mixture Model"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_GaussianMixture:
    """Gaussian Mixture - Probabilistic clustering with GMM"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_components': {'default': 2, 'values': [2,3,4], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "GaussianMixture", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_comp = params.get('n_components', 2)
        
        # Feature: returns
        returns = data['close'].pct_change().fillna(0)
        
        # Simplified GMM: fit Gaussians to return distribution
        gmm_prob = pd.Series(0.0, index=data.index)
        component_label = pd.Series(0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i]
            
            # Fit multiple Gaussians (simplified)
            # Component 1: Positive returns
            positive_returns = window[window > 0]
            if len(positive_returns) > 0:
                mu1 = positive_returns.mean()
                sigma1 = positive_returns.std()
            else:
                mu1, sigma1 = 0, 1
            
            # Component 2: Negative returns
            negative_returns = window[window < 0]
            if len(negative_returns) > 0:
                mu2 = negative_returns.mean()
                sigma2 = negative_returns.std()
            else:
                mu2, sigma2 = 0, 1
            
            # Current return
            current_return = returns.iloc[i]
            
            # Probability under each component
            prob1 = np.exp(-0.5 * ((current_return - mu1) / (sigma1 + 1e-10))**2)
            prob2 = np.exp(-0.5 * ((current_return - mu2) / (sigma2 + 1e-10))**2)
            
            # Assign to most likely component
            if prob1 > prob2:
                component_label.iloc[i] = 1
                gmm_prob.iloc[i] = prob1 / (prob1 + prob2 + 1e-10)
            else:
                component_label.iloc[i] = 0
                gmm_prob.iloc[i] = prob2 / (prob1 + prob2 + 1e-10)
        
        # Smooth
        gmm_smooth = gmm_prob.rolling(5).mean()
        
        # Component stability
        component_stability = (component_label == component_label.shift(1)).rolling(10).mean()
        
        return pd.DataFrame({
            'gmm_prob': gmm_prob,
            'gmm_smooth': gmm_smooth,
            'component_label': component_label,
            'component_stability': component_stability
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High probability in positive component
        entries = (result['component_label'] == 1) & (result['gmm_smooth'] > 0.6)
        
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
            'signal_strength': result['component_stability']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive component
        entries = result['component_label'] == 1
        
        # Exit: Component change
        exits = result['component_label'].diff() != 0
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('component_change', index=data.index),
            'signal_strength': result['component_stability']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['gmm_prob'] = result['gmm_prob']
        features['gmm_smooth'] = result['gmm_smooth']
        features['gmm_component'] = result['component_label']
        features['gmm_stability'] = result['component_stability']
        features['gmm_positive_component'] = (result['component_label'] == 1).astype(int)
        
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

