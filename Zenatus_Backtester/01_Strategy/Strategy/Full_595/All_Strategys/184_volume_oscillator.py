"""184 - Volume Oscillator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeOscillator:
    """Volume Oscillator - Difference between fast and slow volume MAs"""
    PARAMETERS = {
        'fast_period': {'default': 5, 'values': [3,5,7,8,11,13], 'optimize': True},
        'slow_period': {'default': 20, 'values': [14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeOscillator", "Volume", __version__
    
    def calculate(self, data, params):
        fast = params.get('fast_period', 5)
        slow = params.get('slow_period', 20)
        
        # Fast and slow volume MAs
        vol_fast = data['volume'].rolling(fast).mean()
        vol_slow = data['volume'].rolling(slow).mean()
        
        # Volume oscillator
        vol_osc = ((vol_fast - vol_slow) / vol_slow * 100).fillna(0)
        
        # Signal line
        vol_signal = vol_osc.rolling(9).mean()
        
        # Histogram
        vol_hist = vol_osc - vol_signal
        
        # Crossovers
        cross_up = (vol_osc > vol_signal) & (vol_osc.shift(1) <= vol_signal.shift(1))
        cross_down = (vol_osc < vol_signal) & (vol_osc.shift(1) >= vol_signal.shift(1))
        
        return pd.DataFrame({
            'vol_osc': vol_osc,
            'vol_signal': vol_signal,
            'vol_hist': vol_hist,
            'cross_up': cross_up.astype(int),
            'cross_down': cross_down.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Oscillator crosses above signal
        entries = result['cross_up'] == 1
        
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
            'signal_strength': abs(result['vol_hist']) / 100
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Oscillator crosses above signal
        entries = result['cross_up'] == 1
        
        # Exit: Oscillator crosses below signal
        exits = result['cross_down'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vol_osc_cross', index=data.index),
            'signal_strength': abs(result['vol_hist']) / 100
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vol_osc'] = result['vol_osc']
        features['vol_signal'] = result['vol_signal']
        features['vol_hist'] = result['vol_hist']
        features['vol_osc_positive'] = (result['vol_osc'] > 0).astype(int)
        features['vol_above_signal'] = (result['vol_osc'] > result['vol_signal']).astype(int)
        features['vol_cross_up'] = result['cross_up']
        features['vol_cross_down'] = result['cross_down']
        features['vol_hist_slope'] = result['vol_hist'].diff()
        
        return features
    
    def validate_params(self, params):
        pass
