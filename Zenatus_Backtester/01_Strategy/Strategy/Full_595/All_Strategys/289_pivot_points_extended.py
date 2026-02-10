"""289 - Pivot Points Extended"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PivotPointsExtended:
    """Pivot Points Extended - Multiple pivot calculation methods"""
    PARAMETERS = {
        'method': {'default': 'standard', 'values': ['standard', 'fibonacci', 'woodie', 'camarilla'], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PivotPointsExtended", "Patterns", __version__
    
    def calculate(self, data, params):
        method = params.get('method', 'standard')
        
        # Daily high, low, close (resample to daily)
        daily_high = data['high'].resample('D').max().reindex(data.index, method='ffill')
        daily_low = data['low'].resample('D').min().reindex(data.index, method='ffill')
        daily_close = data['close'].resample('D').last().reindex(data.index, method='ffill')
        
        # Pivot Point
        pivot = (daily_high + daily_low + daily_close) / 3
        
        if method == 'standard':
            # Standard Pivot Points
            r1 = 2 * pivot - daily_low
            r2 = pivot + (daily_high - daily_low)
            r3 = daily_high + 2 * (pivot - daily_low)
            s1 = 2 * pivot - daily_high
            s2 = pivot - (daily_high - daily_low)
            s3 = daily_low - 2 * (daily_high - pivot)
            
        elif method == 'fibonacci':
            # Fibonacci Pivot Points
            r1 = pivot + 0.382 * (daily_high - daily_low)
            r2 = pivot + 0.618 * (daily_high - daily_low)
            r3 = pivot + 1.000 * (daily_high - daily_low)
            s1 = pivot - 0.382 * (daily_high - daily_low)
            s2 = pivot - 0.618 * (daily_high - daily_low)
            s3 = pivot - 1.000 * (daily_high - daily_low)
            
        elif method == 'woodie':
            # Woodie Pivot Points
            pivot = (daily_high + daily_low + 2 * daily_close) / 4
            r1 = 2 * pivot - daily_low
            r2 = pivot + (daily_high - daily_low)
            r3 = daily_high + 2 * (pivot - daily_low)
            s1 = 2 * pivot - daily_high
            s2 = pivot - (daily_high - daily_low)
            s3 = daily_low - 2 * (daily_high - pivot)
            
        else:  # camarilla
            # Camarilla Pivot Points
            r1 = daily_close + 1.1 * (daily_high - daily_low) / 12
            r2 = daily_close + 1.1 * (daily_high - daily_low) / 6
            r3 = daily_close + 1.1 * (daily_high - daily_low) / 4
            s1 = daily_close - 1.1 * (daily_high - daily_low) / 12
            s2 = daily_close - 1.1 * (daily_high - daily_low) / 6
            s3 = daily_close - 1.1 * (daily_high - daily_low) / 4
        
        # Distance from pivot
        distance_from_pivot = (data['close'] - pivot) / pivot * 100
        
        return pd.DataFrame({
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3,
            'distance_from_pivot': distance_from_pivot
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above pivot
        entries = (data['close'] > result['pivot']) & (data['close'].shift(1) <= result['pivot'].shift(1))
        
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
            'signal_strength': abs(result['distance_from_pivot']) / 10
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above pivot
        entries = (data['close'] > result['pivot']) & (data['close'].shift(1) <= result['pivot'].shift(1))
        
        # Exit: Price crosses below pivot
        exits = (data['close'] < result['pivot']) & (data['close'].shift(1) >= result['pivot'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pivot_cross', index=data.index),
            'signal_strength': abs(result['distance_from_pivot']) / 10
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['pivot'] = result['pivot']
        features['distance_from_pivot'] = result['distance_from_pivot']
        features['above_pivot'] = (data['close'] > result['pivot']).astype(int)
        features['near_r1'] = (abs(data['close'] - result['r1']) < 0.001).astype(int)
        features['near_s1'] = (abs(data['close'] - result['s1']) < 0.001).astype(int)
        features['above_r1'] = (data['close'] > result['r1']).astype(int)
        features['below_s1'] = (data['close'] < result['s1']).astype(int)
        features['pivot_range'] = result['r1'] - result['s1']
        
        return features
    
    def validate_params(self, params):
        pass
