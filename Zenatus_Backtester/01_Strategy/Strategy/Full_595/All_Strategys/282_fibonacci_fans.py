"""282 - Fibonacci Fans"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FibonacciFans:
    """Fibonacci Fans - Diagonal Support/Resistance Lines"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [30,50,100], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FibonacciFans", "Patterns", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        close = data['close']
        
        # Calculate trend line
        swing_high = close.rolling(period).max()
        swing_low = close.rolling(period).min()
        
        # Time component for fan lines
        time_index = pd.Series(range(len(close)), index=close.index)
        time_normalized = time_index / period
        
        # Fibonacci fan lines (diagonal)
        fib_range = swing_high - swing_low
        
        fan_382 = swing_low + fib_range * 0.382 * (1 - np.exp(-time_normalized * 0.1))
        fan_500 = swing_low + fib_range * 0.500 * (1 - np.exp(-time_normalized * 0.1))
        fan_618 = swing_low + fib_range * 0.618 * (1 - np.exp(-time_normalized * 0.1))
        
        # Price position relative to fans
        above_382 = (close > fan_382).astype(int)
        above_500 = (close > fan_500).astype(int)
        above_618 = (close > fan_618).astype(int)
        
        # Fan strength
        fan_strength = above_382 + above_500 + above_618
        
        return pd.DataFrame({
            'fan_382': fan_382,
            'fan_500': fan_500,
            'fan_618': fan_618,
            'above_382': above_382,
            'above_500': above_500,
            'above_618': above_618,
            'fan_strength': fan_strength
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        fan_data = self.calculate(data, params)
        entries = (data['close'] > fan_data['fan_618']) & (data['close'].shift(1) <= fan_data['fan_618'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': fan_data['fan_strength']/3}
    
    def generate_signals_dynamic(self, data, params):
        fan_data = self.calculate(data, params)
        entries = (data['close'] > fan_data['fan_618']) & (data['close'].shift(1) <= fan_data['fan_618'].shift(1))
        exits = (data['close'] < fan_data['fan_382']) & (data['close'].shift(1) >= fan_data['fan_382'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_fan_382', index=data.index),
                'signal_strength': fan_data['fan_strength']/3}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
