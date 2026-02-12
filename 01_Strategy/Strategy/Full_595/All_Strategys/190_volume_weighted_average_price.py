"""190 - Volume Weighted Average Price (VWAP) Extended"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeWeightedAveragePrice:
    """VWAP Extended - Volume Weighted Average Price with bands"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'std_mult': {'default': 2.0, 'values': [1.0,1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VWAPExtended", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        std_mult = params.get('std_mult', 2.0)
        
        # Typical price
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        
        # VWAP
        vwap = (typical_price * data['volume']).rolling(period).sum() / data['volume'].rolling(period).sum()
        
        # VWAP standard deviation
        vwap_std = typical_price.rolling(period).std()
        
        # VWAP bands
        upper_band = vwap + std_mult * vwap_std
        lower_band = vwap - std_mult * vwap_std
        
        # Distance from VWAP
        distance = (data['close'] - vwap) / vwap * 100
        
        # VWAP slope
        vwap_slope = vwap.diff()
        
        return pd.DataFrame({
            'vwap': vwap,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'vwap_std': vwap_std,
            'distance': distance,
            'vwap_slope': vwap_slope
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above VWAP
        entries = (data['close'] > result['vwap']) & (data['close'].shift(1) <= result['vwap'].shift(1))
        
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
            'signal_strength': abs(result['distance']) / 10
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above VWAP
        entries = (data['close'] > result['vwap']) & (data['close'].shift(1) <= result['vwap'].shift(1))
        
        # Exit: Price crosses below VWAP
        exits = (data['close'] < result['vwap']) & (data['close'].shift(1) >= result['vwap'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vwap_cross', index=data.index),
            'signal_strength': abs(result['distance']) / 10
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vwap'] = result['vwap']
        features['distance_vwap'] = result['distance']
        features['vwap_slope'] = result['vwap_slope']
        features['above_vwap'] = (data['close'] > result['vwap']).astype(int)
        features['above_upper_band'] = (data['close'] > result['upper_band']).astype(int)
        features['below_lower_band'] = (data['close'] < result['lower_band']).astype(int)
        features['vwap_bandwidth'] = (result['upper_band'] - result['lower_band']) / result['vwap']
        features['vwap_position'] = (data['close'] - result['lower_band']) / (result['upper_band'] - result['lower_band'] + 1e-10)
        
        return features
    
    def validate_params(self, params):
        pass
