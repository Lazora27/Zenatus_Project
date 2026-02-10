"""407 - Effective Spread"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_EffectiveSpread:
    """Effective Spread - Realized transaction cost"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "EffectiveSpread", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Mid price
        mid_price = (data['high'] + data['low']) / 2
        
        # Trade price (close)
        trade_price = data['close']
        
        # Effective spread = 2 * |trade_price - mid_price|
        effective_spread = 2 * abs(trade_price - mid_price)
        
        # Relative effective spread
        relative_effective_spread = effective_spread / mid_price
        
        # Average effective spread
        avg_effective_spread = relative_effective_spread.rolling(period).mean()
        
        # Realized spread (price impact component)
        future_mid = mid_price.shift(-1)
        realized_spread = 2 * (trade_price - future_mid)
        realized_spread = realized_spread.fillna(0)
        
        # Price impact = effective - realized
        price_impact = effective_spread - abs(realized_spread)
        
        # Efficiency score (low spread = efficient)
        efficiency = 1 / (avg_effective_spread + 1e-10)
        efficiency_normalized = efficiency / efficiency.rolling(50).max()
        
        # Smooth
        efficiency_smooth = efficiency_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'effective_spread': effective_spread,
            'relative_effective_spread': relative_effective_spread,
            'avg_effective_spread': avg_effective_spread,
            'realized_spread': realized_spread,
            'price_impact': price_impact,
            'efficiency': efficiency_normalized,
            'efficiency_smooth': efficiency_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High efficiency (low spread)
        entries = result['efficiency_smooth'] > 0.7
        
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
            'signal_strength': result['efficiency_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Efficient
        entries = result['efficiency'] > 0.7
        
        # Exit: Inefficient
        exits = result['efficiency'] < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('high_spread', index=data.index),
            'signal_strength': result['efficiency_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['eff_spread'] = result['effective_spread']
        features['eff_spread_relative'] = result['relative_effective_spread']
        features['eff_spread_avg'] = result['avg_effective_spread']
        features['eff_spread_realized'] = result['realized_spread']
        features['eff_spread_price_impact'] = result['price_impact']
        features['eff_spread_efficiency'] = result['efficiency']
        features['eff_spread_efficiency_smooth'] = result['efficiency_smooth']
        features['eff_spread_efficient'] = (result['efficiency'] > 0.7).astype(int)
        
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

