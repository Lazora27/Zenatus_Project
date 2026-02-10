"""071 - PGO (Pretty Good Oscillator)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PGO:
    """PGO - Pretty Good Oscillator"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PGO", "Momentum", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # SMA
        sma = data['close'].rolling(period).mean()
        
        # ATR
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift(1))
        tr3 = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # PGO = (Close - SMA) / ATR
        pgo = (data['close'] - sma) / (atr + 1e-10)
        
        return pgo.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        pgo = self.calculate(data, params)
        # Entry when PGO crosses above 0
        entries = (pgo > 0) & (pgo.shift(1) <= 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(pgo).clip(0, 5) / 5}
    
    def generate_signals_dynamic(self, data, params):
        pgo = self.calculate(data, params)
        entries = (pgo > 0) & (pgo.shift(1) <= 0)
        exits = (pgo < 0) & (pgo.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('pgo_cross', index=data.index),
                'signal_strength': abs(pgo).clip(0, 5) / 5}
    
    def get_ml_features(self, data, params):
        pgo = self.calculate(data, params)
        return pd.DataFrame({'pgo_value': pgo, 'pgo_slope': pgo.diff(),
                           'pgo_positive': (pgo > 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
