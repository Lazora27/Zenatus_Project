"""194 - Volume Intensity"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeIntensity:
    """Volume Intensity - Measures strength of volume relative to price movement"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'threshold': {'default': 1.5, 'values': [1.0,1.2,1.5,1.8,2.0,2.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeIntensity", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        threshold = params.get('threshold', 1.5)
        
        # Price change
        price_change = abs(data['close'] - data['close'].shift(1))
        
        # Volume intensity = Volume / Price Change
        vol_intensity = data['volume'] / (price_change + 1e-10)
        
        # Normalized intensity
        vol_intensity_ma = vol_intensity.rolling(period).mean()
        vol_intensity_std = vol_intensity.rolling(period).std()
        vol_intensity_zscore = (vol_intensity - vol_intensity_ma) / (vol_intensity_std + 1e-10)
        
        # High/Low intensity
        high_intensity = vol_intensity > vol_intensity_ma * threshold
        low_intensity = vol_intensity < vol_intensity_ma / threshold
        
        # Intensity trend
        intensity_slope = vol_intensity.diff()
        
        return pd.DataFrame({
            'vol_intensity': vol_intensity,
            'vol_intensity_ma': vol_intensity_ma,
            'vol_intensity_zscore': vol_intensity_zscore,
            'high_intensity': high_intensity.astype(int),
            'low_intensity': low_intensity.astype(int),
            'intensity_slope': intensity_slope
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High intensity with upward price movement
        price_up = data['close'] > data['close'].shift(1)
        entries = (result['high_intensity'] == 1) & price_up
        
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
            'signal_strength': result['vol_intensity_zscore'].clip(-3, 3) / 3
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High intensity
        entries = result['high_intensity'] == 1
        
        # Exit: Low intensity
        exits = result['low_intensity'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('intensity_change', index=data.index),
            'signal_strength': result['vol_intensity_zscore'].clip(-3, 3) / 3
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vol_intensity'] = result['vol_intensity']
        features['vol_intensity_ma'] = result['vol_intensity_ma']
        features['vol_intensity_zscore'] = result['vol_intensity_zscore']
        features['high_intensity'] = result['high_intensity']
        features['low_intensity'] = result['low_intensity']
        features['intensity_slope'] = result['intensity_slope']
        features['intensity_ratio'] = result['vol_intensity'] / (result['vol_intensity_ma'] + 1e-10)
        features['intensity_extreme'] = (abs(result['vol_intensity_zscore']) > 2).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
