"""164 - Fibonacci Extension"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FibonacciExtension:
    """Fibonacci Extension - Fibonacci projection levels"""
    PARAMETERS = {
        'lookback': {'default': 50, 'values': [30,40,50,60], 'optimize': True},
        'proximity': {'default': 0.005, 'values': [0.003,0.005,0.01], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FibonacciExtension", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 50)
        proximity = params.get('proximity', 0.005)
        
        # Extension ratios
        ext_ratios = [1.0, 1.272, 1.414, 1.618, 2.0, 2.618]
        
        # Calculate extension levels
        ext_levels = pd.DataFrame(index=data.index)
        
        for i in range(lookback, len(data)):
            # Find swing points (A, B, C for ABC pattern)
            window = data.iloc[i-lookback:i]
            
            # Simplified: use high and low
            point_a = window['low'].min()
            point_b = window['high'].max()
            point_c_idx = window['low'].iloc[int(len(window)*0.7):].idxmin()
            point_c = window.loc[point_c_idx, 'low'] if point_c_idx in window.index else point_a
            
            # Calculate move
            move_ab = point_b - point_a
            
            # Extension levels from point C
            for ratio in ext_ratios:
                level = point_c + (move_ab * ratio)
                ext_levels.loc[data.index[i], f'ext_{int(ratio*1000)}'] = level
        
        # Fill forward
        ext_levels = ext_levels.fillna(method='ffill')
        
        # Check proximity to key extension levels (1.272, 1.618, 2.618)
        near_1272 = abs(data['close'] - ext_levels['ext_1272']) / data['close'] < proximity
        near_1618 = abs(data['close'] - ext_levels['ext_1618']) / data['close'] < proximity
        near_2618 = abs(data['close'] - ext_levels['ext_2618']) / data['close'] < proximity
        
        # Signal: approaching extension target
        signal = pd.Series(0, index=data.index)
        signal[near_1272] = 1
        signal[near_1618] = 2
        signal[near_2618] = 3  # Major target
        
        return pd.DataFrame({
            'signal': signal,
            'ext_1000': ext_levels['ext_1000'],
            'ext_1272': ext_levels['ext_1272'],
            'ext_1414': ext_levels['ext_1414'],
            'ext_1618': ext_levels['ext_1618'],
            'ext_2000': ext_levels['ext_2000'],
            'ext_2618': ext_levels['ext_2618']
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        fib_ext = self.calculate(data, params)
        # Entry when moving toward extension levels
        entries = (data['close'] > fib_ext['ext_1000']) & (data['close'] < fib_ext['ext_1618'])
        
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
                'signal_strength': fib_ext['signal'] / 3}
    
    def generate_signals_dynamic(self, data, params):
        fib_ext = self.calculate(data, params)
        entries = (data['close'] > fib_ext['ext_1000']) & (data['close'] < fib_ext['ext_1618'])
        # Exit at major extension level
        exits = (fib_ext['signal'] >= 2)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('ext_target', index=data.index),
                'signal_strength': fib_ext['signal'] / 3}
    
    def get_ml_features(self, data, params):
        fib_ext = self.calculate(data, params)
        return pd.DataFrame({
            'ext_signal': fib_ext['signal'],
            'ext_near_1272': (fib_ext['signal'] == 1).astype(int),
            'ext_near_1618': (fib_ext['signal'] == 2).astype(int),
            'ext_near_2618': (fib_ext['signal'] == 3).astype(int),
            'ext_progress': (data['close'] - fib_ext['ext_1000']) / (fib_ext['ext_2618'] - fib_ext['ext_1000'] + 1e-10)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
