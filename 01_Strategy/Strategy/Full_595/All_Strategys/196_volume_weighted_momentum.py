"""196 - Volume Weighted Momentum"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeWeightedMomentum:
    """Volume Weighted Momentum - Momentum adjusted by volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,20,21,23], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeWeightedMomentum", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Price momentum
        price_momentum = data['close'] - data['close'].shift(period)
        
        # Volume weight
        vol_weight = data['volume'] / data['volume'].rolling(period).mean()
        
        # Volume weighted momentum
        vw_momentum = price_momentum * vol_weight
        
        # Signal line
        vw_momentum_signal = vw_momentum.rolling(9).mean()
        
        # Histogram
        vw_momentum_hist = vw_momentum - vw_momentum_signal
        
        # Normalized
        vw_momentum_norm = vw_momentum / (abs(vw_momentum).rolling(50).mean() + 1e-10)
        
        # Crossovers
        cross_up = (vw_momentum > vw_momentum_signal) & (vw_momentum.shift(1) <= vw_momentum_signal.shift(1))
        cross_down = (vw_momentum < vw_momentum_signal) & (vw_momentum.shift(1) >= vw_momentum_signal.shift(1))
        
        return pd.DataFrame({
            'vw_momentum': vw_momentum,
            'vw_momentum_signal': vw_momentum_signal,
            'vw_momentum_hist': vw_momentum_hist,
            'vw_momentum_norm': vw_momentum_norm,
            'cross_up': cross_up.astype(int),
            'cross_down': cross_down.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Momentum crosses above signal
        entries = result['cross_up'] == 1
        
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
            'signal_strength': abs(result['vw_momentum_norm']).clip(0, 3) / 3
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Momentum crosses above signal
        entries = result['cross_up'] == 1
        
        # Exit: Momentum crosses below signal
        exits = result['cross_down'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('momentum_reversal', index=data.index),
            'signal_strength': abs(result['vw_momentum_norm']).clip(0, 3) / 3
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vw_momentum'] = result['vw_momentum']
        features['vw_momentum_signal'] = result['vw_momentum_signal']
        features['vw_momentum_hist'] = result['vw_momentum_hist']
        features['vw_momentum_norm'] = result['vw_momentum_norm']
        features['vw_momentum_positive'] = (result['vw_momentum'] > 0).astype(int)
        features['vw_momentum_above_signal'] = (result['vw_momentum'] > result['vw_momentum_signal']).astype(int)
        features['cross_up'] = result['cross_up']
        features['cross_down'] = result['cross_down']
        
        return features
    
    def validate_params(self, params):
        pass
