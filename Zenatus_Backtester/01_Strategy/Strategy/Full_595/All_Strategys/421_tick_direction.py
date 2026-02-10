"""421 - Tick Direction Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TickDirection:
    """Tick Direction - Classifies ticks as uptick/downtick"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TickDirection", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Tick direction (price change)
        price_change = data['close'].diff()
        
        # Classify ticks
        uptick = (price_change > 0).astype(int)
        downtick = (price_change < 0).astype(int)
        zero_tick = (price_change == 0).astype(int)
        
        # Tick imbalance
        tick_imbalance = uptick - downtick
        
        # Cumulative tick imbalance
        cumulative_tick_imbalance = tick_imbalance.rolling(period).sum()
        
        # Tick ratio
        total_ticks = (uptick + downtick).rolling(period).sum()
        uptick_ratio = uptick.rolling(period).sum() / (total_ticks + 1e-10)
        
        # Tick momentum
        tick_momentum = tick_imbalance.rolling(5).mean()
        
        # Signal strength
        signal_strength = abs(cumulative_tick_imbalance) / period
        signal_strength = signal_strength.clip(0, 1)
        
        # Bullish signal
        bullish_signal = uptick_ratio
        
        # Smooth
        bullish_smooth = bullish_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'uptick': uptick,
            'downtick': downtick,
            'zero_tick': zero_tick,
            'tick_imbalance': tick_imbalance,
            'cumulative_tick_imbalance': cumulative_tick_imbalance,
            'uptick_ratio': uptick_ratio,
            'tick_momentum': tick_momentum,
            'signal_strength': signal_strength,
            'bullish_signal': bullish_signal,
            'bullish_smooth': bullish_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong uptick bias
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
        
        # Entry: Bullish
        entries = result['uptick_ratio'] > 0.6
        
        # Exit: Bearish
        exits = result['uptick_ratio'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('tick_reversal', index=data.index),
            'signal_strength': result['signal_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['tick_uptick'] = result['uptick']
        features['tick_downtick'] = result['downtick']
        features['tick_zero'] = result['zero_tick']
        features['tick_imbalance'] = result['tick_imbalance']
        features['tick_cumulative_imbalance'] = result['cumulative_tick_imbalance']
        features['tick_uptick_ratio'] = result['uptick_ratio']
        features['tick_momentum'] = result['tick_momentum']
        features['tick_signal_strength'] = result['signal_strength']
        features['tick_bullish'] = result['bullish_signal']
        features['tick_bullish_smooth'] = result['bullish_smooth']
        features['tick_strong_bullish'] = (result['uptick_ratio'] > 0.6).astype(int)
        
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

