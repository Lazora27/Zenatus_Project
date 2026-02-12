"""185 - Volume Divergence"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeDivergence:
    """Volume Divergence - Detects price/volume divergences"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'lookback': {'default': 5, 'values': [3,5,7,8,11], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeDivergence", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        lookback = params.get('lookback', 5)
        
        # Price momentum
        price_momentum = data['close'].diff(period)
        
        # Volume momentum
        vol_momentum = data['volume'].diff(period)
        
        # Detect divergences
        # Bullish: Price down, Volume up
        bullish_div = (price_momentum < 0) & (vol_momentum > 0)
        
        # Bearish: Price up, Volume down
        bearish_div = (price_momentum > 0) & (vol_momentum < 0)
        
        # Divergence strength
        price_change_pct = abs(price_momentum / data['close'].shift(period)) * 100
        vol_change_pct = abs(vol_momentum / data['volume'].shift(period)) * 100
        div_strength = (price_change_pct + vol_change_pct) / 2
        
        # Confirmation (divergence persists)
        bullish_confirmed = bullish_div.rolling(lookback).sum() >= 3
        bearish_confirmed = bearish_div.rolling(lookback).sum() >= 3
        
        return pd.DataFrame({
            'price_momentum': price_momentum,
            'vol_momentum': vol_momentum,
            'bullish_div': bullish_div.astype(int),
            'bearish_div': bearish_div.astype(int),
            'div_strength': div_strength,
            'bullish_confirmed': bullish_confirmed.astype(int),
            'bearish_confirmed': bearish_confirmed.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Confirmed bullish divergence
        entries = result['bullish_confirmed'] == 1
        
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
            'signal_strength': result['div_strength'].clip(0, 10) / 10
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Confirmed bullish divergence
        entries = result['bullish_confirmed'] == 1
        
        # Exit: Bearish divergence appears
        exits = result['bearish_div'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('divergence_reversal', index=data.index),
            'signal_strength': result['div_strength'].clip(0, 10) / 10
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['price_momentum'] = result['price_momentum']
        features['vol_momentum'] = result['vol_momentum']
        features['bullish_div'] = result['bullish_div']
        features['bearish_div'] = result['bearish_div']
        features['div_strength'] = result['div_strength']
        features['bullish_confirmed'] = result['bullish_confirmed']
        features['bearish_confirmed'] = result['bearish_confirmed']
        features['any_divergence'] = (result['bullish_div'] | result['bearish_div']).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
