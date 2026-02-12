"""074 - Rainbow Oscillator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Rainbow:
    """Rainbow - Multi-Period Moving Average Oscillator"""
    PARAMETERS = {
        'max_period': {'default': 10, 'values': [5,7,8,10,12,14,17], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Rainbow", "Trend", __version__
    
    def calculate(self, data, params):
        max_period = params.get('max_period', 10)
        
        # Calculate multiple SMAs
        mas = [data['close'].rolling(i).mean() for i in range(2, max_period + 1)]
        
        # Average of all MAs
        rainbow_avg = pd.concat(mas, axis=1).mean(axis=1)
        
        # Rainbow Oscillator = (Close - Rainbow Average) / Rainbow Average * 100
        rainbow = ((data['close'] - rainbow_avg) / (rainbow_avg + 1e-10) * 100).fillna(0)
        
        return rainbow
    
    def generate_signals_fixed(self, data, params):
        rainbow = self.calculate(data, params)
        # Entry when crosses above 0
        entries = (rainbow > 0) & (rainbow.shift(1) <= 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(rainbow).clip(0, 10) / 10}
    
    def generate_signals_dynamic(self, data, params):
        rainbow = self.calculate(data, params)
        entries = (rainbow > 0) & (rainbow.shift(1) <= 0)
        exits = (rainbow < 0) & (rainbow.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('rainbow_cross', index=data.index),
                'signal_strength': abs(rainbow).clip(0, 10) / 10}
    
    def get_ml_features(self, data, params):
        rainbow = self.calculate(data, params)
        return pd.DataFrame({'rainbow_value': rainbow, 'rainbow_slope': rainbow.diff(),
                           'rainbow_positive': (rainbow > 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
