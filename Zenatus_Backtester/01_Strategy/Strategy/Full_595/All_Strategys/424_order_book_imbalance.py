"""424 - Order Book Imbalance"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_OrderBookImbalance:
    """Order Book Imbalance - Estimated from price and volume"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "OrderBookImbalance", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Estimate bid/ask volumes from price position in range
        price_range = data['high'] - data['low']
        
        # Position in range (0 = low, 1 = high)
        price_position = (data['close'] - data['low']) / (price_range + 1e-10)
        
        # Estimate bid/ask volumes
        # Close near high = more buying = bid volume > ask volume
        bid_volume = data['volume'] * price_position
        ask_volume = data['volume'] * (1 - price_position)
        
        # Order book imbalance
        obi = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-10)
        
        # Average OBI
        avg_obi = obi.rolling(period).mean()
        
        # OBI momentum
        obi_momentum = obi.diff()
        
        # OBI volatility
        obi_volatility = obi.rolling(period).std()
        
        # Cumulative OBI
        cumulative_obi = obi.rolling(period).sum()
        
        # Signal strength
        signal_strength = abs(avg_obi)
        
        # Bullish signal
        bullish_signal = (obi + 1) / 2  # Normalize to [0, 1]
        
        # Smooth
        bullish_smooth = bullish_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'price_position': price_position,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'obi': obi,
            'avg_obi': avg_obi,
            'obi_momentum': obi_momentum,
            'obi_volatility': obi_volatility,
            'cumulative_obi': cumulative_obi,
            'signal_strength': signal_strength,
            'bullish_signal': bullish_signal,
            'bullish_smooth': bullish_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong bid side
        entries = result['bullish_smooth'] > 0.6
        
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
        
        # Entry: Bid pressure
        entries = result['obi'] > 0.3
        
        # Exit: Ask pressure
        exits = result['obi'] < -0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('obi_reversal', index=data.index),
            'signal_strength': result['signal_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['obi_price_position'] = result['price_position']
        features['obi_bid_volume'] = result['bid_volume']
        features['obi_ask_volume'] = result['ask_volume']
        features['obi_value'] = result['obi']
        features['obi_avg'] = result['avg_obi']
        features['obi_momentum'] = result['obi_momentum']
        features['obi_volatility'] = result['obi_volatility']
        features['obi_cumulative'] = result['cumulative_obi']
        features['obi_signal_strength'] = result['signal_strength']
        features['obi_bullish'] = result['bullish_signal']
        features['obi_bullish_smooth'] = result['bullish_smooth']
        features['obi_bid_pressure'] = (result['obi'] > 0.3).astype(int)
        
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

