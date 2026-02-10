"""333 - Feature Interaction Detector"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FeatureInteraction:
    """Feature Interaction - Detects interactions between features"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FeatureInteraction", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Base features
        returns = data['close'].pct_change()
        
        # Feature 1: Trend
        sma = data['close'].rolling(period).mean()
        trend = (data['close'] > sma).astype(float)
        
        # Feature 2: Volume
        vol_ma = data['volume'].rolling(period).mean()
        volume_high = (data['volume'] > vol_ma).astype(float)
        
        # Feature 3: Volatility
        volatility = returns.rolling(period).std()
        vol_low = (volatility < volatility.rolling(50).median()).astype(float)
        
        # Interaction 1: Trend + Volume (strong signal)
        interaction_1 = trend * volume_high
        
        # Interaction 2: Trend + Low Volatility (stable trend)
        interaction_2 = trend * vol_low
        
        # Interaction 3: Volume + Low Volatility (accumulation)
        interaction_3 = volume_high * vol_low
        
        # Combined interaction score
        interaction_score = (
            0.4 * interaction_1 +
            0.3 * interaction_2 +
            0.3 * interaction_3
        )
        
        # Smooth
        interaction_smooth = interaction_score.rolling(5).mean()
        
        # Interaction strength
        interaction_strength = (interaction_1 + interaction_2 + interaction_3) / 3
        
        return pd.DataFrame({
            'interaction_1': interaction_1,
            'interaction_2': interaction_2,
            'interaction_3': interaction_3,
            'interaction_score': interaction_score,
            'interaction_smooth': interaction_smooth,
            'interaction_strength': interaction_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong interaction
        entries = result['interaction_smooth'] > 0.5
        
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
            'signal_strength': result['interaction_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong interaction
        entries = result['interaction_smooth'] > 0.5
        
        # Exit: Weak interaction
        exits = result['interaction_smooth'] < 0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('interaction_break', index=data.index),
            'signal_strength': result['interaction_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['interaction_1'] = result['interaction_1']
        features['interaction_2'] = result['interaction_2']
        features['interaction_3'] = result['interaction_3']
        features['interaction_score'] = result['interaction_score']
        features['interaction_smooth'] = result['interaction_smooth']
        features['interaction_strength'] = result['interaction_strength']
        features['strong_interaction'] = (result['interaction_smooth'] > 0.6).astype(int)
        
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

