"""192 - Volume Accumulation Distribution Extended"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeAccumulationDistribution:
    """Volume Accumulation Distribution - Extended A/D Line with analysis"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeAccumulationDistribution", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Money Flow Multiplier
        clv = ((data['close'] - data['low']) - (data['high'] - data['close'])) / (data['high'] - data['low'] + 1e-10)
        
        # Money Flow Volume
        mfv = clv * data['volume']
        
        # Accumulation/Distribution Line
        ad_line = mfv.cumsum()
        
        # A/D Signal line
        ad_signal = ad_line.rolling(period).mean()
        
        # A/D slope
        ad_slope = ad_line.diff()
        
        # A/D divergence
        price_slope = data['close'].diff()
        bullish_div = (ad_slope > 0) & (price_slope < 0)
        bearish_div = (ad_slope < 0) & (price_slope > 0)
        
        return pd.DataFrame({
            'ad_line': ad_line,
            'ad_signal': ad_signal,
            'ad_slope': ad_slope,
            'clv': clv,
            'mfv': mfv,
            'bullish_div': bullish_div.astype(int),
            'bearish_div': bearish_div.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: A/D crosses above signal
        entries = (result['ad_line'] > result['ad_signal']) & (result['ad_line'].shift(1) <= result['ad_signal'].shift(1))
        
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
            'signal_strength': abs(result['clv'])
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: A/D crosses above signal
        entries = (result['ad_line'] > result['ad_signal']) & (result['ad_line'].shift(1) <= result['ad_signal'].shift(1))
        
        # Exit: A/D crosses below signal
        exits = (result['ad_line'] < result['ad_signal']) & (result['ad_line'].shift(1) >= result['ad_signal'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('ad_cross', index=data.index),
            'signal_strength': abs(result['clv'])
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ad_line'] = result['ad_line']
        features['ad_signal'] = result['ad_signal']
        features['ad_slope'] = result['ad_slope']
        features['clv'] = result['clv']
        features['mfv'] = result['mfv']
        features['ad_above_signal'] = (result['ad_line'] > result['ad_signal']).astype(int)
        features['bullish_div'] = result['bullish_div']
        features['bearish_div'] = result['bearish_div']
        features['ad_slope_positive'] = (result['ad_slope'] > 0).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
