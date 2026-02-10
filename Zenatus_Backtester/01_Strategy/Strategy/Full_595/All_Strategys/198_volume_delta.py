"""198 - Volume Delta"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeDelta:
    """Volume Delta - Difference between buying and selling volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeDelta", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Estimate buying/selling volume based on price position in bar
        bar_range = data['high'] - data['low']
        close_position = (data['close'] - data['low']) / (bar_range + 1e-10)
        
        # Buying volume (when close near high)
        buying_volume = data['volume'] * close_position
        
        # Selling volume (when close near low)
        selling_volume = data['volume'] * (1 - close_position)
        
        # Volume Delta
        volume_delta = buying_volume - selling_volume
        
        # Cumulative Volume Delta
        cvd = volume_delta.cumsum()
        
        # CVD signal line
        cvd_signal = cvd.rolling(period).mean()
        
        # Delta ratio
        delta_ratio = buying_volume / (selling_volume + 1e-10)
        
        # Delta strength
        delta_strength = volume_delta / (data['volume'] + 1e-10)
        
        return pd.DataFrame({
            'buying_volume': buying_volume,
            'selling_volume': selling_volume,
            'volume_delta': volume_delta,
            'cvd': cvd,
            'cvd_signal': cvd_signal,
            'delta_ratio': delta_ratio,
            'delta_strength': delta_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: CVD crosses above signal (buying pressure)
        entries = (result['cvd'] > result['cvd_signal']) & (result['cvd'].shift(1) <= result['cvd_signal'].shift(1))
        
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
            'signal_strength': abs(result['delta_strength'])
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: CVD crosses above signal
        entries = (result['cvd'] > result['cvd_signal']) & (result['cvd'].shift(1) <= result['cvd_signal'].shift(1))
        
        # Exit: CVD crosses below signal
        exits = (result['cvd'] < result['cvd_signal']) & (result['cvd'].shift(1) >= result['cvd_signal'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('cvd_reversal', index=data.index),
            'signal_strength': abs(result['delta_strength'])
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['buying_volume'] = result['buying_volume']
        features['selling_volume'] = result['selling_volume']
        features['volume_delta'] = result['volume_delta']
        features['cvd'] = result['cvd']
        features['delta_ratio'] = result['delta_ratio']
        features['delta_strength'] = result['delta_strength']
        features['buying_pressure'] = (result['volume_delta'] > 0).astype(int)
        features['cvd_above_signal'] = (result['cvd'] > result['cvd_signal']).astype(int)
        features['delta_ratio_high'] = (result['delta_ratio'] > 1.5).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
