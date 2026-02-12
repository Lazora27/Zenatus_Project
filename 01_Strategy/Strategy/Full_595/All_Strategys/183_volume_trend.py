"""183 - Volume Trend"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeTrend:
    """Volume Trend - Identifies volume trends"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeTrend", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Volume moving averages
        vol_sma = data['volume'].rolling(period).mean()
        vol_ema = data['volume'].ewm(span=period).mean()
        
        # Volume trend (linear regression slope)
        def calc_slope(x):
            if len(x) < 2:
                return 0
            y = np.arange(len(x))
            slope = np.polyfit(y, x, 1)[0]
            return slope
        
        vol_slope = data['volume'].rolling(period).apply(calc_slope, raw=True)
        
        # Volume trend strength
        vol_std = data['volume'].rolling(period).std()
        vol_trend_strength = abs(vol_slope) / (vol_std + 1e-10)
        
        # Increasing/decreasing volume
        vol_increasing = vol_slope > 0
        vol_decreasing = vol_slope < 0
        
        return pd.DataFrame({
            'vol_sma': vol_sma,
            'vol_ema': vol_ema,
            'vol_slope': vol_slope,
            'vol_trend_strength': vol_trend_strength,
            'vol_increasing': vol_increasing.astype(int),
            'vol_decreasing': vol_decreasing.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Volume trend turns positive with price uptrend
        price_uptrend = data['close'] > data['close'].shift(1)
        entries = (result['vol_increasing'] == 1) & price_uptrend
        
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
            'signal_strength': result['vol_trend_strength'].clip(0, 1)
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Volume trend turns positive
        entries = (result['vol_increasing'] == 1) & (result['vol_increasing'].shift(1) == 0)
        
        # Exit: Volume trend turns negative
        exits = (result['vol_decreasing'] == 1) & (result['vol_decreasing'].shift(1) == 0)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vol_trend_change', index=data.index),
            'signal_strength': result['vol_trend_strength'].clip(0, 1)
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vol_sma'] = result['vol_sma']
        features['vol_ema'] = result['vol_ema']
        features['vol_slope'] = result['vol_slope']
        features['vol_trend_strength'] = result['vol_trend_strength']
        features['vol_increasing'] = result['vol_increasing']
        features['vol_decreasing'] = result['vol_decreasing']
        features['vol_above_sma'] = (data['volume'] > result['vol_sma']).astype(int)
        features['vol_sma_ema_diff'] = result['vol_sma'] - result['vol_ema']
        
        return features
    
    def validate_params(self, params):
        pass
