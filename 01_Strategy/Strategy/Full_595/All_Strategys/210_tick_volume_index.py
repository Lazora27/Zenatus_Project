"""210 - Tick Volume Index"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TickVolumeIndex:
    """Tick Volume Index - Analyzes tick volume patterns"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TickVolumeIndex", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Use volume as proxy for tick volume
        tick_volume = data['volume']
        
        # Tick Volume Index (cumulative)
        price_change = data['close'] - data['close'].shift(1)
        tvi = (tick_volume * np.sign(price_change)).cumsum()
        
        # TVI signal line
        tvi_signal = tvi.rolling(period).mean()
        
        # TVI slope
        tvi_slope = tvi.diff()
        
        # Tick volume MA
        tick_vol_ma = tick_volume.rolling(period).mean()
        
        # High tick volume
        high_tick_vol = tick_volume > tick_vol_ma * 1.5
        
        return pd.DataFrame({
            'tvi': tvi,
            'tvi_signal': tvi_signal,
            'tvi_slope': tvi_slope,
            'tick_vol_ma': tick_vol_ma,
            'high_tick_vol': high_tick_vol.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: TVI crosses above signal
        entries = (result['tvi'] > result['tvi_signal']) & (result['tvi'].shift(1) <= result['tvi_signal'].shift(1))
        
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
            'signal_strength': abs(result['tvi_slope']) / (abs(result['tvi_slope']).rolling(50).mean() + 1e-10)
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: TVI crosses above signal
        entries = (result['tvi'] > result['tvi_signal']) & (result['tvi'].shift(1) <= result['tvi_signal'].shift(1))
        
        # Exit: TVI crosses below signal
        exits = (result['tvi'] < result['tvi_signal']) & (result['tvi'].shift(1) >= result['tvi_signal'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('tvi_cross', index=data.index),
            'signal_strength': abs(result['tvi_slope']) / (abs(result['tvi_slope']).rolling(50).mean() + 1e-10)
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['tvi'] = result['tvi']
        features['tvi_signal'] = result['tvi_signal']
        features['tvi_slope'] = result['tvi_slope']
        features['tick_vol_ma'] = result['tick_vol_ma']
        features['high_tick_vol'] = result['high_tick_vol']
        features['tvi_above_signal'] = (result['tvi'] > result['tvi_signal']).astype(int)
        features['tvi_slope_positive'] = (result['tvi_slope'] > 0).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
