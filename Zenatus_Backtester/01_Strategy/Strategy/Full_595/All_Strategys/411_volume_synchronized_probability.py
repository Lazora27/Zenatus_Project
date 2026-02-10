"""411 - Volume Synchronized Probability of Informed Trading"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VPIN:
    """VPIN - Volume Synchronized Probability of Informed Trading"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_buckets': {'default': 50, 'values': [30,50,70], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VPIN", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_buckets = params.get('n_buckets', 50)
        
        # Classify trades as buy/sell
        price_change = data['close'] - data['open']
        
        # Buy volume
        buy_volume = data['volume'].copy()
        buy_volume[price_change < 0] = 0
        
        # Sell volume
        sell_volume = data['volume'].copy()
        sell_volume[price_change > 0] = 0
        
        # Volume imbalance
        volume_imbalance = abs(buy_volume - sell_volume)
        
        # VPIN calculation
        vpin = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Sum over period
            total_imbalance = volume_imbalance.iloc[i-period:i].sum()
            total_volume = data['volume'].iloc[i-period:i].sum()
            
            if total_volume > 0:
                vpin.iloc[i] = total_imbalance / total_volume
        
        # VPIN trend
        vpin_trend = vpin.diff()
        
        # High VPIN = toxic flow (informed trading)
        toxicity = vpin
        
        # Low VPIN = safe to trade
        safety = 1 - vpin
        
        # Smooth
        safety_smooth = safety.rolling(5).mean()
        
        return pd.DataFrame({
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'volume_imbalance': volume_imbalance,
            'vpin': vpin,
            'vpin_trend': vpin_trend,
            'toxicity': toxicity,
            'safety': safety,
            'safety_smooth': safety_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Low VPIN (safe)
        entries = result['safety_smooth'] > 0.6
        
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
            'signal_strength': result['safety_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Safe
        entries = result['safety'] > 0.6
        
        # Exit: Toxic
        exits = result['safety'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('toxic_flow', index=data.index),
            'signal_strength': result['safety_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vpin_buy_volume'] = result['buy_volume']
        features['vpin_sell_volume'] = result['sell_volume']
        features['vpin_imbalance'] = result['volume_imbalance']
        features['vpin_value'] = result['vpin']
        features['vpin_trend'] = result['vpin_trend']
        features['vpin_toxicity'] = result['toxicity']
        features['vpin_safety'] = result['safety']
        features['vpin_safety_smooth'] = result['safety_smooth']
        features['vpin_safe'] = (result['safety'] > 0.6).astype(int)
        
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

