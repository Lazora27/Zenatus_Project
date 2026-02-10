"""163 - Fibonacci Retracement"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FibonacciRetracement:
    """Fibonacci Retracement - Auto Fibonacci levels"""
    PARAMETERS = {
        'lookback': {'default': 50, 'values': [30,40,50,60], 'optimize': True},
        'proximity': {'default': 0.005, 'values': [0.003,0.005,0.01], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FibonacciRetracement", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 50)
        proximity = params.get('proximity', 0.005)
        
        # Fibonacci ratios
        fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        
        # Calculate Fibonacci levels
        fib_levels = pd.DataFrame(index=data.index)
        
        for i in range(lookback, len(data)):
            # Find swing high and low in lookback period
            swing_high = data['high'].iloc[i-lookback:i].max()
            swing_low = data['low'].iloc[i-lookback:i].min()
            
            range_val = swing_high - swing_low
            
            # Calculate Fibonacci levels (for uptrend retracement)
            for ratio in fib_ratios:
                level = swing_high - (range_val * ratio)
                fib_levels.loc[data.index[i], f'fib_{int(ratio*1000)}'] = level
        
        # Fill forward
        fib_levels = fib_levels.fillna(method='ffill')
        
        # Check proximity to key levels (382, 500, 618)
        near_382 = abs(data['close'] - fib_levels['fib_382']) / data['close'] < proximity
        near_500 = abs(data['close'] - fib_levels['fib_500']) / data['close'] < proximity
        near_618 = abs(data['close'] - fib_levels['fib_618']) / data['close'] < proximity
        
        # Signal: near key Fibonacci level
        signal = pd.Series(0, index=data.index)
        signal[near_618] = 3  # Strongest
        signal[near_500] = 2
        signal[near_382] = 1
        
        return pd.DataFrame({
            'signal': signal,
            'fib_0': fib_levels['fib_0'],
            'fib_236': fib_levels['fib_236'],
            'fib_382': fib_levels['fib_382'],
            'fib_500': fib_levels['fib_500'],
            'fib_618': fib_levels['fib_618'],
            'fib_786': fib_levels['fib_786'],
            'fib_1000': fib_levels['fib_1000']
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        fib = self.calculate(data, params)
        # Entry near Fibonacci levels
        entries = (fib['signal'] > 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': fib['signal'] / 3}
    
    def generate_signals_dynamic(self, data, params):
        fib = self.calculate(data, params)
        entries = (fib['signal'] > 0)
        # Exit when price reaches 0% (swing high)
        exits = (data['close'] >= fib['fib_0'])
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('fib_target', index=data.index),
                'signal_strength': fib['signal'] / 3}
    
    def get_ml_features(self, data, params):
        fib = self.calculate(data, params)
        return pd.DataFrame({
            'fib_signal': fib['signal'],
            'fib_position': (data['close'] - fib['fib_1000']) / (fib['fib_0'] - fib['fib_1000'] + 1e-10),
            'fib_near_382': (fib['signal'] == 1).astype(int),
            'fib_near_500': (fib['signal'] == 2).astype(int),
            'fib_near_618': (fib['signal'] == 3).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
