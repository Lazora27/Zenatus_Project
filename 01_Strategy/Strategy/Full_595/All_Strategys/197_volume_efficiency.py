"""197 - Volume Efficiency Ratio"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeEfficiency:
    """Volume Efficiency - Measures how efficiently volume moves price"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeEfficiency", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Price change
        price_change = abs(data['close'] - data['close'].shift(period))
        
        # Volume sum
        volume_sum = data['volume'].rolling(period).sum()
        
        # Volume Efficiency = Price Change / Volume
        vol_efficiency = price_change / (volume_sum + 1e-10)
        
        # Normalized efficiency
        vol_eff_ma = vol_efficiency.rolling(period).mean()
        vol_eff_std = vol_efficiency.rolling(period).std()
        vol_eff_zscore = (vol_efficiency - vol_eff_ma) / (vol_eff_std + 1e-10)
        
        # High/Low efficiency
        high_efficiency = vol_efficiency > vol_eff_ma * 1.5
        low_efficiency = vol_efficiency < vol_eff_ma * 0.5
        
        # Efficiency trend
        eff_slope = vol_efficiency.diff()
        
        # Efficiency percentile
        eff_percentile = vol_efficiency.rolling(100).apply(
            lambda x: pd.Series(x).rank().iloc[-1] / len(x) if len(x) > 0 else 0.5
        )
        
        return pd.DataFrame({
            'vol_efficiency': vol_efficiency,
            'vol_eff_ma': vol_eff_ma,
            'vol_eff_zscore': vol_eff_zscore,
            'high_efficiency': high_efficiency.astype(int),
            'low_efficiency': low_efficiency.astype(int),
            'eff_slope': eff_slope,
            'eff_percentile': eff_percentile
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High efficiency (price moves efficiently)
        entries = result['high_efficiency'] == 1
        
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
            'signal_strength': result['eff_percentile']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High efficiency
        entries = result['high_efficiency'] == 1
        
        # Exit: Low efficiency
        exits = result['low_efficiency'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('efficiency_drop', index=data.index),
            'signal_strength': result['eff_percentile']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vol_efficiency'] = result['vol_efficiency']
        features['vol_eff_ma'] = result['vol_eff_ma']
        features['vol_eff_zscore'] = result['vol_eff_zscore']
        features['high_efficiency'] = result['high_efficiency']
        features['low_efficiency'] = result['low_efficiency']
        features['eff_slope'] = result['eff_slope']
        features['eff_percentile'] = result['eff_percentile']
        features['eff_ratio'] = result['vol_efficiency'] / (result['vol_eff_ma'] + 1e-10)
        
        return features
    
    def validate_params(self, params):
        pass
