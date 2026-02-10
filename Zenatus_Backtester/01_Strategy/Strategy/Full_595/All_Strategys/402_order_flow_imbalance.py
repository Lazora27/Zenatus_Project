"""402 - Order Flow Imbalance"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_OrderFlowImbalance:
    """Order Flow Imbalance - Buy/Sell pressure from volume"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "OrderFlowImbalance", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Estimate buy/sell volume from price movement
        price_change = data['close'] - data['open']
        
        # Buy volume (when price goes up)
        buy_volume = data['volume'].copy()
        buy_volume[price_change < 0] = 0
        
        # Sell volume (when price goes down)
        sell_volume = data['volume'].copy()
        sell_volume[price_change > 0] = 0
        
        # Order flow imbalance
        ofi = buy_volume - sell_volume
        
        # Cumulative OFI
        cumulative_ofi = ofi.rolling(period).sum()
        
        # Normalized OFI
        total_volume = data['volume'].rolling(period).sum()
        ofi_normalized = cumulative_ofi / (total_volume + 1e-10)
        
        # OFI momentum
        ofi_momentum = ofi_normalized.diff()
        
        # Signal strength
        signal_strength = abs(ofi_normalized)
        
        # Smooth
        ofi_smooth = ofi_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'ofi': ofi,
            'cumulative_ofi': cumulative_ofi,
            'ofi_normalized': ofi_normalized,
            'ofi_momentum': ofi_momentum,
            'signal_strength': signal_strength,
            'ofi_smooth': ofi_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong buy pressure
        entries = result['ofi_smooth'] > 0.3
        
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
            'signal_strength': result['signal_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Buy pressure
        entries = result['ofi_normalized'] > 0.2
        
        # Exit: Sell pressure
        exits = result['ofi_normalized'] < -0.2
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('ofi_reversal', index=data.index),
            'signal_strength': result['signal_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['ofi_value'] = result['ofi']
        features['ofi_cumulative'] = result['cumulative_ofi']
        features['ofi_normalized'] = result['ofi_normalized']
        features['ofi_momentum'] = result['ofi_momentum']
        features['ofi_signal_strength'] = result['signal_strength']
        features['ofi_smooth'] = result['ofi_smooth']
        features['ofi_buy_pressure'] = (result['ofi_normalized'] > 0.2).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass

    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100, 150],
            'sl_pips': [15, 25, 35, 50, 75]
        }

