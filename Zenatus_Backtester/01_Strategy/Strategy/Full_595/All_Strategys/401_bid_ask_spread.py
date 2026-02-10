"""401 - Bid-Ask Spread Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BidAskSpread:
    """Bid-Ask Spread - Market liquidity measure"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BidAskSpread", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Estimate bid-ask spread from high-low
        # Spread = High - Low (intrabar range as proxy)
        spread = data['high'] - data['low']
        
        # Relative spread
        mid_price = (data['high'] + data['low']) / 2
        relative_spread = spread / mid_price
        
        # Average spread
        avg_spread = spread.rolling(period).mean()
        
        # Spread volatility
        spread_volatility = spread.rolling(period).std()
        
        # Liquidity score (inverse of spread)
        liquidity = 1 / (relative_spread + 1e-10)
        liquidity_normalized = liquidity / liquidity.rolling(50).max()
        
        # Signal: high liquidity (low spread)
        liquidity_signal = liquidity_normalized
        
        # Smooth
        liquidity_smooth = liquidity_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'spread': spread,
            'relative_spread': relative_spread,
            'avg_spread': avg_spread,
            'spread_volatility': spread_volatility,
            'liquidity': liquidity_normalized,
            'liquidity_smooth': liquidity_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High liquidity
        entries = result['liquidity_smooth'] > 0.7
        
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
            'signal_strength': result['liquidity_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Liquid
        entries = result['liquidity'] > 0.7
        
        # Exit: Illiquid
        exits = result['liquidity'] < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('illiquidity', index=data.index),
            'signal_strength': result['liquidity_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['spread_absolute'] = result['spread']
        features['spread_relative'] = result['relative_spread']
        features['spread_avg'] = result['avg_spread']
        features['spread_volatility'] = result['spread_volatility']
        features['spread_liquidity'] = result['liquidity']
        features['spread_liquidity_smooth'] = result['liquidity_smooth']
        features['spread_high_liquidity'] = (result['liquidity'] > 0.7).astype(int)
        
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

