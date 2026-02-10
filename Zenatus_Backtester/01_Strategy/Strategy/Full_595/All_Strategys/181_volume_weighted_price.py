"""181 - Volume Weighted Price"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeWeightedPrice:
    """Volume Weighted Price - Price weighted by volume"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeWeightedPrice", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Volume Weighted Price
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwp = (typical_price * data['volume']).rolling(period).sum() / data['volume'].rolling(period).sum()
        
        # VWP deviation
        vwp_deviation = (data['close'] - vwp) / vwp * 100
        
        # VWP slope
        vwp_slope = vwp.diff()
        
        # VWP acceleration
        vwp_accel = vwp_slope.diff()
        
        return pd.DataFrame({
            'vwp': vwp,
            'vwp_deviation': vwp_deviation,
            'vwp_slope': vwp_slope,
            'vwp_accel': vwp_accel
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above VWP
        entries = (data['close'] > result['vwp']) & (data['close'].shift(1) <= result['vwp'].shift(1))
        
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
            'signal_strength': abs(result['vwp_deviation']) / 100
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above VWP
        entries = (data['close'] > result['vwp']) & (data['close'].shift(1) <= result['vwp'].shift(1))
        
        # Exit: Price crosses below VWP
        exits = (data['close'] < result['vwp']) & (data['close'].shift(1) >= result['vwp'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vwp_cross', index=data.index),
            'signal_strength': abs(result['vwp_deviation']) / 100
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vwp'] = result['vwp']
        features['vwp_deviation'] = result['vwp_deviation']
        features['vwp_slope'] = result['vwp_slope']
        features['vwp_accel'] = result['vwp_accel']
        features['above_vwp'] = (data['close'] > result['vwp']).astype(int)
        features['vwp_distance'] = data['close'] - result['vwp']
        features['vwp_distance_pct'] = (data['close'] - result['vwp']) / result['vwp'] * 100
        
        return features
    
    def validate_params(self, params):
        pass
