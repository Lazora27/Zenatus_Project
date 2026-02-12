"""132 - Fibonacci Channels"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FibonacciChannels:
    """Fibonacci Channels - Fibonacci ratio-based channels"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [30,40,50,60,75], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FibonacciChannels", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        
        # Find swing high and low
        high = data['high'].rolling(period).max()
        low = data['low'].rolling(period).min()
        
        # Range
        range_val = high - low
        
        # Fibonacci levels (0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
        fib_0 = low
        fib_236 = low + range_val * 0.236
        fib_382 = low + range_val * 0.382
        fib_50 = low + range_val * 0.5
        fib_618 = low + range_val * 0.618
        fib_786 = low + range_val * 0.786
        fib_100 = high
        
        return pd.DataFrame({
            'fib_0': fib_0,
            'fib_236': fib_236,
            'fib_382': fib_382,
            'fib_50': fib_50,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'fib_100': fib_100
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        fib = self.calculate(data, params)
        # Entry when price crosses above 50% level
        entries = (data['close'] > fib['fib_50']) & (data['close'].shift(1) <= fib['fib_50'].shift(1))
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 
                'signal_strength': (data['close'] - fib['fib_0']) / (fib['fib_100'] - fib['fib_0'] + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        fib = self.calculate(data, params)
        entries = (data['close'] > fib['fib_50']) & (data['close'].shift(1) <= fib['fib_50'].shift(1))
        exits = (data['close'] < fib['fib_50']) & (data['close'].shift(1) >= fib['fib_50'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('fib_cross', index=data.index),
                'signal_strength': (data['close'] - fib['fib_0']) / (fib['fib_100'] - fib['fib_0'] + 1e-10)}
    
    def get_ml_features(self, data, params):
        fib = self.calculate(data, params)
        return pd.DataFrame({
            'fib_position': (data['close'] - fib['fib_0']) / (fib['fib_100'] - fib['fib_0'] + 1e-10),
            'near_fib_50': (abs(data['close'] - fib['fib_50']) < 0.001).astype(int),
            'near_fib_618': (abs(data['close'] - fib['fib_618']) < 0.001).astype(int),
            'above_fib_50': (data['close'] > fib['fib_50']).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
