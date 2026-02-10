"""191 - Volume Zone Oscillator (VZO)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeZoneOscillator:
    """Volume Zone Oscillator - Measures volume flow direction"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeZoneOscillator", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Price direction
        price_change = data['close'] - data['close'].shift(1)
        
        # Signed volume
        signed_volume = data['volume'].copy()
        signed_volume[price_change < 0] = -signed_volume[price_change < 0]
        
        # VZO = EMA(signed_volume) / EMA(volume) * 100
        signed_vol_ema = signed_volume.ewm(span=period).mean()
        vol_ema = data['volume'].ewm(span=period).mean()
        
        vzo = (signed_vol_ema / vol_ema * 100).fillna(0)
        
        # Signal line
        vzo_signal = vzo.ewm(span=9).mean()
        
        # Overbought/Oversold
        overbought = vzo > 60
        oversold = vzo < -60
        
        # Zero line crosses
        cross_above_zero = (vzo > 0) & (vzo.shift(1) <= 0)
        cross_below_zero = (vzo < 0) & (vzo.shift(1) >= 0)
        
        return pd.DataFrame({
            'vzo': vzo,
            'vzo_signal': vzo_signal,
            'overbought': overbought.astype(int),
            'oversold': oversold.astype(int),
            'cross_above_zero': cross_above_zero.astype(int),
            'cross_below_zero': cross_below_zero.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: VZO crosses above zero (bullish volume)
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
            'signal_strength': abs(result['vzo']) / 100
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: VZO crosses above zero
        entries = result['cross_above_zero'] == 1
        
        # Exit: VZO crosses below zero
        exits = result['cross_below_zero'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vzo_reversal', index=data.index),
            'signal_strength': abs(result['vzo']) / 100
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vzo'] = result['vzo']
        features['vzo_signal'] = result['vzo_signal']
        features['vzo_positive'] = (result['vzo'] > 0).astype(int)
        features['vzo_overbought'] = result['overbought']
        features['vzo_oversold'] = result['oversold']
        features['vzo_cross_above'] = result['cross_above_zero']
        features['vzo_cross_below'] = result['cross_below_zero']
        features['vzo_above_signal'] = (result['vzo'] > result['vzo_signal']).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
