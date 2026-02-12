"""187 - Volume Profile"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeProfile:
    """Volume Profile - Volume distribution at price levels"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'bins': {'default': 10, 'values': [5,8,10,13,15,20], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeProfile", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        bins = params.get('bins', 10)
        
        # Calculate POC (Point of Control) - price with highest volume
        poc = pd.Series(index=data.index, dtype=float)
        value_area_high = pd.Series(index=data.index, dtype=float)
        value_area_low = pd.Series(index=data.index, dtype=float)
        
        for i in range(period, len(data)):
            window_data = data.iloc[i-period:i]
            
            # Create price bins
            price_min = window_data['low'].min()
            price_max = window_data['high'].max()
            price_bins = np.linspace(price_min, price_max, bins)
            
            # Assign volume to bins
            typical_price = (window_data['high'] + window_data['low'] + window_data['close']) / 3
            vol_profile = np.zeros(bins-1)
            
            for j, (tp, vol) in enumerate(zip(typical_price, window_data['volume'])):
                bin_idx = np.digitize(tp, price_bins) - 1
                if 0 <= bin_idx < len(vol_profile):
                    vol_profile[bin_idx] += vol
            
            # POC = price level with highest volume
            if len(vol_profile) > 0 and vol_profile.sum() > 0:
                poc_idx = np.argmax(vol_profile)
                poc.iloc[i] = (price_bins[poc_idx] + price_bins[poc_idx+1]) / 2
                
                # Value area (70% of volume)
                sorted_idx = np.argsort(vol_profile)[::-1]
                cumsum = 0
                total_vol = vol_profile.sum()
                value_bins = []
                
                for idx in sorted_idx:
                    cumsum += vol_profile[idx]
                    value_bins.append(idx)
                    if cumsum >= total_vol * 0.7:
                        break
                
                if value_bins:
                    value_area_high.iloc[i] = price_bins[max(value_bins)+1]
                    value_area_low.iloc[i] = price_bins[min(value_bins)]
        
        # Fill NaN
        poc = poc.fillna(method='ffill')
        value_area_high = value_area_high.fillna(method='ffill')
        value_area_low = value_area_low.fillna(method='ffill')
        
        # Distance from POC
        distance_from_poc = (data['close'] - poc) / poc * 100
        
        return pd.DataFrame({
            'poc': poc,
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'distance_from_poc': distance_from_poc
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above POC
        entries = (data['close'] > result['poc']) & (data['close'].shift(1) <= result['poc'].shift(1))
        
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
            'signal_strength': abs(result['distance_from_poc']) / 10
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above POC
        entries = (data['close'] > result['poc']) & (data['close'].shift(1) <= result['poc'].shift(1))
        
        # Exit: Price crosses below POC
        exits = (data['close'] < result['poc']) & (data['close'].shift(1) >= result['poc'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('poc_cross', index=data.index),
            'signal_strength': abs(result['distance_from_poc']) / 10
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['poc'] = result['poc']
        features['value_area_high'] = result['value_area_high']
        features['value_area_low'] = result['value_area_low']
        features['distance_from_poc'] = result['distance_from_poc']
        features['above_poc'] = (data['close'] > result['poc']).astype(int)
        features['in_value_area'] = ((data['close'] >= result['value_area_low']) & (data['close'] <= result['value_area_high'])).astype(int)
        features['above_value_area'] = (data['close'] > result['value_area_high']).astype(int)
        features['below_value_area'] = (data['close'] < result['value_area_low']).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
