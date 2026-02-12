"""093 - Laguerre Filter"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Laguerre:
    """Laguerre Filter - Ehlers"""
    PARAMETERS = {
        'gamma': {'default': 0.8, 'values': [0.5,0.6,0.7,0.8,0.85,0.9], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Laguerre", "Trend", __version__
    
    def calculate(self, data, params):
        gamma = params.get('gamma', 0.8)
        
        # Laguerre Filter
        l0 = pd.Series(index=data.index, dtype=float)
        l1 = pd.Series(index=data.index, dtype=float)
        l2 = pd.Series(index=data.index, dtype=float)
        l3 = pd.Series(index=data.index, dtype=float)
        
        l0.iloc[0] = data['close'].iloc[0]
        l1.iloc[0] = data['close'].iloc[0]
        l2.iloc[0] = data['close'].iloc[0]
        l3.iloc[0] = data['close'].iloc[0]
        
        for i in range(1, len(data)):
            l0.iloc[i] = (1 - gamma) * data['close'].iloc[i] + gamma * l0.iloc[i-1]
            l1.iloc[i] = -gamma * l0.iloc[i] + l0.iloc[i-1] + gamma * l1.iloc[i-1]
            l2.iloc[i] = -gamma * l1.iloc[i] + l1.iloc[i-1] + gamma * l2.iloc[i-1]
            l3.iloc[i] = -gamma * l2.iloc[i] + l2.iloc[i-1] + gamma * l3.iloc[i-1]
        
        # Laguerre = (L0 + 2*L1 + 2*L2 + L3) / 6
        laguerre = (l0 + 2 * l1 + 2 * l2 + l3) / 6
        
        return laguerre.fillna(data['close'])
    
    def generate_signals_fixed(self, data, params):
        laguerre = self.calculate(data, params)
        # Entry when price crosses above Laguerre
        entries = (data['close'] > laguerre) & (data['close'].shift(1) <= laguerre.shift(1))
        
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
                'signal_strength': abs(data['close'] - laguerre) / (laguerre + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        laguerre = self.calculate(data, params)
        entries = (data['close'] > laguerre) & (data['close'].shift(1) <= laguerre.shift(1))
        exits = (data['close'] < laguerre) & (data['close'].shift(1) >= laguerre.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('laguerre_cross', index=data.index),
                'signal_strength': abs(data['close'] - laguerre) / (laguerre + 1e-10)}
    
    def get_ml_features(self, data, params):
        laguerre = self.calculate(data, params)
        return pd.DataFrame({'laguerre_value': laguerre, 'laguerre_slope': laguerre.diff(),
                           'price_above_laguerre': (data['close'] > laguerre).astype(int),
                           'distance_from_laguerre': data['close'] - laguerre}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
