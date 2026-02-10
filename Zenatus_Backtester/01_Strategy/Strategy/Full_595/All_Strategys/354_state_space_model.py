"""354 - State Space Model"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_StateSpaceModel:
    """State Space Model - Hidden state estimation"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "StateSpaceModel", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # State space representation
        # State: [level, velocity]
        # Observation: price
        
        returns = data['close'].pct_change().fillna(0)
        
        # Hidden states
        level_state = pd.Series(data['close'].iloc[0], index=data.index)
        velocity_state = pd.Series(0.0, index=data.index)
        
        # State transition
        for i in range(1, len(data)):
            # Predict
            level_pred = level_state.iloc[i-1] + velocity_state.iloc[i-1]
            velocity_pred = velocity_state.iloc[i-1]
            
            # Update with observation
            innovation = data['close'].iloc[i] - level_pred
            
            # Kalman-like update
            level_state.iloc[i] = level_pred + 0.5 * innovation
            velocity_state.iloc[i] = velocity_pred + 0.1 * innovation
        
        # State-based signal
        # Positive velocity = uptrend
        state_signal = (velocity_state > 0).astype(float)
        
        # Smooth
        state_smooth = state_signal.rolling(5).mean()
        
        # State confidence (low innovation = good model)
        innovation = abs(data['close'] - level_state)
        confidence = 1 - innovation.rolling(period).mean() / data['close'].rolling(period).std()
        confidence = confidence.clip(0, 1)
        
        return pd.DataFrame({
            'level_state': level_state,
            'velocity_state': velocity_state,
            'state_signal': state_signal,
            'state_smooth': state_smooth,
            'confidence': confidence
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive velocity state
        entries = result['state_smooth'] > 0.6
        
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
        
        # Entry: Positive velocity
        entries = result['state_smooth'] > 0.6
        
        # Exit: Negative velocity
        exits = result['state_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('state_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ssm_level'] = result['level_state']
        features['ssm_velocity'] = result['velocity_state']
        features['ssm_signal'] = result['state_signal']
        features['ssm_smooth'] = result['state_smooth']
        features['ssm_confidence'] = result['confidence']
        features['ssm_positive_velocity'] = (result['velocity_state'] > 0).astype(int)
        
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

