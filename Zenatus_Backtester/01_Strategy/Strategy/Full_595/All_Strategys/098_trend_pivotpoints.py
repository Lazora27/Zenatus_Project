"""098 - Pivot Points (Standard)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PivotPoints:
    """Pivot Points - Support and Resistance Levels"""
    PARAMETERS = {
        'period': {'default': 1, 'values': [1], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PivotPoints", "Support/Resistance", __version__
    
    def calculate(self, data, params):
        # Daily Pivot Points (using previous period)
        pivot = (data['high'].shift(1) + data['low'].shift(1) + data['close'].shift(1)) / 3
        
        # Support and Resistance
        r1 = 2 * pivot - data['low'].shift(1)
        s1 = 2 * pivot - data['high'].shift(1)
        r2 = pivot + (data['high'].shift(1) - data['low'].shift(1))
        s2 = pivot - (data['high'].shift(1) - data['low'].shift(1))
        
        return pd.DataFrame({
            'pivot': pivot.fillna(data['close']),
            'r1': r1.fillna(data['close']),
            's1': s1.fillna(data['close']),
            'r2': r2.fillna(data['close']),
            's2': s2.fillna(data['close'])
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        pp = self.calculate(data, params)
        # Entry when price crosses above pivot
        entries = (data['close'] > pp['pivot']) & (data['close'].shift(1) <= pp['pivot'].shift(1))
        
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
                'signal_strength': abs(data['close'] - pp['pivot']) / (pp['pivot'] + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        pp = self.calculate(data, params)
        entries = (data['close'] > pp['pivot']) & (data['close'].shift(1) <= pp['pivot'].shift(1))
        exits = (data['close'] < pp['pivot']) & (data['close'].shift(1) >= pp['pivot'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('pivot_cross', index=data.index),
                'signal_strength': abs(data['close'] - pp['pivot']) / (pp['pivot'] + 1e-10)}
    
    def get_ml_features(self, data, params):
        pp = self.calculate(data, params)
        return pd.DataFrame({'pivot': pp['pivot'], 'r1': pp['r1'], 's1': pp['s1'],
                           'above_pivot': (data['close'] > pp['pivot']).astype(int),
                           'near_r1': (abs(data['close'] - pp['r1']) < 0.001).astype(int),
                           'near_s1': (abs(data['close'] - pp['s1']) < 0.001).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
