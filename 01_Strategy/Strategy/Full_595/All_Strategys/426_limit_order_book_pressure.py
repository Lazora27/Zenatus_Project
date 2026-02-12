"""426 - Limit Order Book Pressure"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_LimitOrderBookPressure:
    """Limit Order Book Pressure - Buy/sell pressure from order book"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "LOBPressure", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Estimate LOB pressure from price action
        # Strong move up = bid pressure, Strong move down = ask pressure
        
        # Price momentum
        price_momentum = data['close'].diff()
        
        # Volume-weighted momentum
        vw_momentum = price_momentum * data['volume']
        
        # Cumulative pressure
        cumulative_pressure = vw_momentum.rolling(period).sum()
        
        # Normalize
        total_volume = data['volume'].rolling(period).sum()
        pressure_normalized = cumulative_pressure / (total_volume + 1e-10)
        
        # Bid pressure (positive)
        bid_pressure = pressure_normalized.clip(lower=0)
        
        # Ask pressure (negative, make positive)
        ask_pressure = (-pressure_normalized).clip(lower=0)
        
        # Net pressure
        net_pressure = bid_pressure - ask_pressure
        
        # Pressure imbalance
        pressure_imbalance = (bid_pressure - ask_pressure) / (bid_pressure + ask_pressure + 1e-10)
        
        # Signal strength
        signal_strength = abs(pressure_imbalance)
        
        # Bullish signal
        bullish_signal = (pressure_imbalance + 1) / 2  # Normalize to [0, 1]
        
        # Smooth
        bullish_smooth = bullish_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'vw_momentum': vw_momentum,
            'cumulative_pressure': cumulative_pressure,
            'pressure_normalized': pressure_normalized,
            'bid_pressure': bid_pressure,
            'ask_pressure': ask_pressure,
            'net_pressure': net_pressure,
            'pressure_imbalance': pressure_imbalance,
            'signal_strength': signal_strength,
            'bullish_signal': bullish_signal,
            'bullish_smooth': bullish_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong bid pressure
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
        entries = result['pressure_imbalance'] > 0.3
        
        # Exit: Ask pressure
        exits = result['pressure_imbalance'] < -0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pressure_reversal', index=data.index),
            'signal_strength': result['signal_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['lob_vw_momentum'] = result['vw_momentum']
        features['lob_cumulative_pressure'] = result['cumulative_pressure']
        features['lob_pressure_normalized'] = result['pressure_normalized']
        features['lob_bid_pressure'] = result['bid_pressure']
        features['lob_ask_pressure'] = result['ask_pressure']
        features['lob_net_pressure'] = result['net_pressure']
        features['lob_pressure_imbalance'] = result['pressure_imbalance']
        features['lob_signal_strength'] = result['signal_strength']
        features['lob_bullish'] = result['bullish_signal']
        features['lob_bullish_smooth'] = result['bullish_smooth']
        features['lob_strong_bid'] = (result['pressure_imbalance'] > 0.3).astype(int)
        
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

