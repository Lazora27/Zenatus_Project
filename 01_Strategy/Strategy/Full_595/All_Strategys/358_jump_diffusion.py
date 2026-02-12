"""358 - Jump Diffusion Model"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_JumpDiffusion:
    """Jump Diffusion - Detects jumps in price process"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'jump_threshold': {'default': 2.0, 'values': [1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "JumpDiffusion", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('jump_threshold', 2.0)
        
        # Returns
        returns = data['close'].pct_change().fillna(0)
        
        # Diffusion component (continuous)
        diffusion_vol = returns.rolling(period).std()
        
        # Jump detection
        # Jump if return exceeds threshold * volatility
        expected_return = returns.rolling(period).mean()
        
        jump_size = abs(returns - expected_return) / (diffusion_vol + 1e-10)
        is_jump = jump_size > threshold
        
        # Jump direction
        jump_direction = np.sign(returns)
        
        # Jump intensity (frequency)
        jump_intensity = is_jump.rolling(period).mean()
        
        # Post-jump behavior
        post_jump_returns = pd.Series(0.0, index=data.index)
        
        for i in range(1, len(data)):
            if is_jump.iloc[i-1]:
                # Return after jump
                post_jump_returns.iloc[i] = returns.iloc[i]
        
        # Average post-jump return
        post_jump_avg = post_jump_returns.rolling(period).mean()
        
        # Signal: positive jumps lead to continuation
        jump_signal = (is_jump & (jump_direction > 0)).astype(float)
        
        # Smooth
        jump_smooth = jump_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'jump_size': jump_size,
            'is_jump': is_jump.astype(int),
            'jump_intensity': jump_intensity,
            'jump_signal': jump_signal,
            'jump_smooth': jump_smooth,
            'post_jump_avg': post_jump_avg
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive jump detected
        entries = result['jump_signal'] > 0.5
        
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
            'signal_strength': result['jump_intensity']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Jump detected
        entries = result['is_jump'] == 1
        
        # Exit: After 5 periods
        exits = result['is_jump'].shift(5) == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('post_jump', index=data.index),
            'signal_strength': result['jump_intensity']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['jump_size'] = result['jump_size']
        features['jump_detected'] = result['is_jump']
        features['jump_intensity'] = result['jump_intensity']
        features['jump_signal'] = result['jump_signal']
        features['jump_smooth'] = result['jump_smooth']
        features['jump_post_avg'] = result['post_jump_avg']
        
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

