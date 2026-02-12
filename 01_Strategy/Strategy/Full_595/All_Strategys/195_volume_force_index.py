"""195 - Volume Force Index Extended"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeForceIndex:
    """Volume Force Index - Extended version with multiple timeframes"""
    PARAMETERS = {
        'short_period': {'default': 2, 'values': [1,2,3,5,7], 'optimize': True},
        'long_period': {'default': 13, 'values': [8,11,13,14,17,19,21], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeForceIndex", "Volume", __version__
    
    def calculate(self, data, params):
        short = params.get('short_period', 2)
        long = params.get('long_period', 13)
        
        # Raw Force Index = (Close - Close[1]) * Volume
        raw_fi = (data['close'] - data['close'].shift(1)) * data['volume']
        
        # Short-term Force Index
        fi_short = raw_fi.ewm(span=short).mean()
        
        # Long-term Force Index
        fi_long = raw_fi.ewm(span=long).mean()
        
        # Force Index Oscillator
        fi_osc = fi_short - fi_long
        
        # Normalized Force Index
        fi_normalized = raw_fi / (abs(raw_fi).rolling(50).mean() + 1e-10)
        
        # Zero crosses
        cross_above_zero = (fi_short > 0) & (fi_short.shift(1) <= 0)
        cross_below_zero = (fi_short < 0) & (fi_short.shift(1) >= 0)
        
        return pd.DataFrame({
            'raw_fi': raw_fi,
            'fi_short': fi_short,
            'fi_long': fi_long,
            'fi_osc': fi_osc,
            'fi_normalized': fi_normalized,
            'cross_above_zero': cross_above_zero.astype(int),
            'cross_below_zero': cross_below_zero.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Short FI crosses above zero
        entries = result['cross_above_zero'] == 1
        
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
            'signal_strength': abs(result['fi_normalized']).clip(0, 3) / 3
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Short FI crosses above zero
        entries = result['cross_above_zero'] == 1
        
        # Exit: Short FI crosses below zero
        exits = result['cross_below_zero'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('fi_reversal', index=data.index),
            'signal_strength': abs(result['fi_normalized']).clip(0, 3) / 3
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['raw_fi'] = result['raw_fi']
        features['fi_short'] = result['fi_short']
        features['fi_long'] = result['fi_long']
        features['fi_osc'] = result['fi_osc']
        features['fi_normalized'] = result['fi_normalized']
        features['fi_short_positive'] = (result['fi_short'] > 0).astype(int)
        features['fi_long_positive'] = (result['fi_long'] > 0).astype(int)
        features['fi_alignment'] = ((result['fi_short'] > 0) & (result['fi_long'] > 0)).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
