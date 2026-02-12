"""337 - ICA Signal Separator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ICASignal:
    """ICA Signal - Independent Component Analysis for signal separation"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ICASignal", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Mixed signals (trend + noise + volume)
        returns = data['close'].pct_change()
        
        # Signal 1: Trend component
        sma = data['close'].rolling(period).mean()
        trend_signal = (data['close'] - sma).fillna(0)
        
        # Signal 2: Momentum component
        momentum = (data['close'] - data['close'].shift(5)).fillna(0)
        
        # Signal 3: Volume component
        vol_change = data['volume'].pct_change().fillna(0)
        
        # Create mixed signals
        mixed = pd.DataFrame({
            'mix1': trend_signal + 0.5 * momentum + 0.3 * vol_change,
            'mix2': 0.5 * trend_signal + momentum + 0.2 * vol_change,
            'mix3': 0.3 * trend_signal + 0.3 * momentum + vol_change
        })
        
        # Simplified ICA: decorrelation
        ica_components = pd.DataFrame(index=data.index)
        
        for i in range(period, len(data)):
            window = mixed.iloc[i-period:i]
            
            if len(window) > 0:
                # Center data
                centered = window - window.mean()
                
                # Whitening (decorrelation)
                cov = centered.cov()
                
                try:
                    eigenvalues, eigenvectors = np.linalg.eig(cov)
                    
                    # Whitening matrix
                    D = np.diag(1.0 / np.sqrt(eigenvalues + 1e-10))
                    whitening = eigenvectors @ D @ eigenvectors.T
                    
                    # Apply whitening to current observation
                    current = mixed.iloc[i].values - window.mean().values
                    whitened = whitening @ current
                    
                    # First independent component
                    ica_components.loc[data.index[i], 'ic1'] = whitened[0]
                    
                except:
                    ica_components.loc[data.index[i], 'ic1'] = 0
        
        ica_score = ica_components['ic1'].fillna(0)
        
        # Normalize to probability
        ica_prob = 1 / (1 + np.exp(-2 * ica_score))
        
        # Smooth
        ica_smooth = ica_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'ica_score': ica_score,
            'ica_prob': ica_prob,
            'ica_smooth': ica_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High ICA score
        entries = result['ica_smooth'] > 0.6
        
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
            'signal_strength': result['ica_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['ica_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['ica_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('ica_reversal', index=data.index),
            'signal_strength': result['ica_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ica_score'] = result['ica_score']
        features['ica_prob'] = result['ica_prob']
        features['ica_smooth'] = result['ica_smooth']
        features['ica_high_score'] = (result['ica_smooth'] > 0.6).astype(int)
        features['ica_low_score'] = (result['ica_smooth'] < 0.4).astype(int)
        
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

