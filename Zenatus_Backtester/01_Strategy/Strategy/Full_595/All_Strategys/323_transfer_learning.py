"""323 - Transfer Learning Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TransferLearning:
    """Transfer Learning - Applies learned patterns from different timeframes"""
    PARAMETERS = {
        'short_period': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'long_period': {'default': 20, 'values': [14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TransferLearning", "Statistics", __version__
    
    def calculate(self, data, params):
        short = params.get('short_period', 5)
        long = params.get('long_period', 20)
        
        # Learn from long-term patterns
        returns = data['close'].pct_change()
        
        # Long-term pattern
        long_trend = data['close'].rolling(long).mean()
        long_pattern = (data['close'] > long_trend).astype(float)
        
        # Transfer to short-term
        short_trend = data['close'].rolling(short).mean()
        short_pattern = (data['close'] > short_trend).astype(float)
        
        # Transfer score: alignment between timeframes
        transfer_score = (long_pattern + short_pattern) / 2
        
        # Pattern consistency
        consistency = (long_pattern == short_pattern).rolling(10).mean()
        
        # Momentum transfer
        long_momentum = data['close'] - data['close'].shift(long)
        short_momentum = data['close'] - data['close'].shift(short)
        
        momentum_alignment = ((long_momentum > 0) == (short_momentum > 0)).astype(float)
        
        # Combined transfer signal
        transfer_signal = (transfer_score + momentum_alignment) / 2
        
        # Smooth
        transfer_smooth = transfer_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'transfer_score': transfer_score,
            'transfer_signal': transfer_signal,
            'transfer_smooth': transfer_smooth,
            'consistency': consistency,
            'momentum_alignment': momentum_alignment
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong transfer signal
        entries = result['transfer_smooth'] > 0.7
        
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
            'signal_strength': result['consistency']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong signal
        entries = result['transfer_smooth'] > 0.7
        
        # Exit: Signal weakens
        exits = result['transfer_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('transfer_break', index=data.index),
            'signal_strength': result['consistency']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['transfer_score'] = result['transfer_score']
        features['transfer_signal'] = result['transfer_signal']
        features['transfer_smooth'] = result['transfer_smooth']
        features['transfer_consistency'] = result['consistency']
        features['transfer_momentum_align'] = result['momentum_alignment']
        features['transfer_strong'] = (result['transfer_smooth'] > 0.7).astype(int)
        features['transfer_weak'] = (result['transfer_smooth'] < 0.4).astype(int)
        
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

