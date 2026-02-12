"""188 - Volume Price Trend (VPT)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumePriceTrend:
    """Volume Price Trend - Cumulative volume based on price changes"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21,23], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumePriceTrend", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Price change percentage
        price_change_pct = (data['close'] - data['close'].shift(1)) / data['close'].shift(1)
        
        # VPT = cumulative (volume * price_change_pct)
        vpt = (data['volume'] * price_change_pct).cumsum()
        
        # VPT signal line
        vpt_signal = vpt.rolling(period).mean()
        
        # VPT slope
        vpt_slope = vpt.diff()
        
        # VPT divergence from price
        price_slope = data['close'].diff()
        vpt_price_div = (vpt_slope > 0) & (price_slope < 0)  # Bullish
        
        return pd.DataFrame({
            'vpt': vpt,
            'vpt_signal': vpt_signal,
            'vpt_slope': vpt_slope,
            'vpt_above_signal': (vpt > vpt_signal).astype(int),
            'vpt_price_div': vpt_price_div.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: VPT crosses above signal
        entries = (result['vpt'] > result['vpt_signal']) & (result['vpt'].shift(1) <= result['vpt_signal'].shift(1))
        
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
            'signal_strength': abs(result['vpt_slope']) / (abs(result['vpt_slope']).rolling(50).mean() + 1e-10)
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: VPT crosses above signal
        entries = (result['vpt'] > result['vpt_signal']) & (result['vpt'].shift(1) <= result['vpt_signal'].shift(1))
        
        # Exit: VPT crosses below signal
        exits = (result['vpt'] < result['vpt_signal']) & (result['vpt'].shift(1) >= result['vpt_signal'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vpt_cross', index=data.index),
            'signal_strength': abs(result['vpt_slope']) / (abs(result['vpt_slope']).rolling(50).mean() + 1e-10)
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vpt'] = result['vpt']
        features['vpt_signal'] = result['vpt_signal']
        features['vpt_slope'] = result['vpt_slope']
        features['vpt_above_signal'] = result['vpt_above_signal']
        features['vpt_price_div'] = result['vpt_price_div']
        features['vpt_normalized'] = (result['vpt'] - result['vpt'].rolling(100).min()) / (result['vpt'].rolling(100).max() - result['vpt'].rolling(100).min() + 1e-10)
        features['vpt_slope_positive'] = (result['vpt_slope'] > 0).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
