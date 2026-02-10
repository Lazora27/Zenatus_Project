"""193 - Volume Price Confirmation Index (VPCI)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumePriceConfirmation:
    """Volume Price Confirmation - Confirms price moves with volume"""
    PARAMETERS = {
        'short_period': {'default': 5, 'values': [3,5,7,8,11], 'optimize': True},
        'long_period': {'default': 20, 'values': [14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumePriceConfirmation", "Volume", __version__
    
    def calculate(self, data, params):
        short = params.get('short_period', 5)
        long = params.get('long_period', 20)
        
        # Volume moving averages
        vwma_short = (data['close'] * data['volume']).rolling(short).sum() / data['volume'].rolling(short).sum()
        vwma_long = (data['close'] * data['volume']).rolling(long).sum() / data['volume'].rolling(long).sum()
        
        # Price moving averages
        sma_short = data['close'].rolling(short).mean()
        sma_long = data['close'].rolling(long).mean()
        
        # VPCI = (VWMA - SMA) / SMA * 100
        vpci_short = (vwma_short - sma_short) / sma_short * 100
        vpci_long = (vwma_long - sma_long) / sma_long * 100
        
        # Confirmation signal
        confirmed_uptrend = (vpci_short > 0) & (vpci_long > 0)
        confirmed_downtrend = (vpci_short < 0) & (vpci_long < 0)
        
        # Divergence
        divergence = (vpci_short > 0) & (vpci_long < 0)
        
        return pd.DataFrame({
            'vpci_short': vpci_short,
            'vpci_long': vpci_long,
            'vwma_short': vwma_short,
            'vwma_long': vwma_long,
            'confirmed_uptrend': confirmed_uptrend.astype(int),
            'confirmed_downtrend': confirmed_downtrend.astype(int),
            'divergence': divergence.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Confirmed uptrend
        entries = result['confirmed_uptrend'] == 1
        
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
            'signal_strength': (abs(result['vpci_short']) + abs(result['vpci_long'])) / 20
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Confirmed uptrend
        entries = result['confirmed_uptrend'] == 1
        
        # Exit: Confirmed downtrend
        exits = result['confirmed_downtrend'] == 1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('vpci_reversal', index=data.index),
            'signal_strength': (abs(result['vpci_short']) + abs(result['vpci_long'])) / 20
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vpci_short'] = result['vpci_short']
        features['vpci_long'] = result['vpci_long']
        features['vpci_diff'] = result['vpci_short'] - result['vpci_long']
        features['confirmed_uptrend'] = result['confirmed_uptrend']
        features['confirmed_downtrend'] = result['confirmed_downtrend']
        features['divergence'] = result['divergence']
        features['vpci_short_positive'] = (result['vpci_short'] > 0).astype(int)
        features['vpci_long_positive'] = (result['vpci_long'] > 0).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass
