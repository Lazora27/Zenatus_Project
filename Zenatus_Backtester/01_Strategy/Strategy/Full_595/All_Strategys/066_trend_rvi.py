"""066 - RVI (Relative Vigor Index)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"
class Indicator_RVI:
    """RVI - Relative Vigor Index"""
    PARAMETERS = {'period': {'default': 10, 'values': [5,7,8,10,11,13,14,17,19,21], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category, self.version = "RVI", "Momentum", __version__
    def calculate(self, data, params): p = params.get('period', 10); num = ((data['close'] - data['open']) + 2 * (data['close'].shift(1) - data['open'].shift(1)) + 2 * (data['close'].shift(2) - data['open'].shift(2)) + (data['close'].shift(3) - data['open'].shift(3))) / 6; den = ((data['high'] - data['low']) + 2 * (data['high'].shift(1) - data['low'].shift(1)) + 2 * (data['high'].shift(2) - data['low'].shift(2)) + (data['high'].shift(3) - data['low'].shift(3))) / 6; rvi = num.rolling(p).sum() / (den.rolling(p).sum() + 1e-10); signal = (rvi + 2 * rvi.shift(1) + 2 * rvi.shift(2) + rvi.shift(3)) / 6; return pd.DataFrame({'rvi': rvi.fillna(0), 'signal': signal.fillna(0)}, index=data.index)
    def generate_signals_fixed(self, data, params):
        r = self.calculate(data, params)
        entries = (r['rvi'] > r['signal']) & (r['rvi'].shift(1) <= r['signal'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(r['rvi'] - r['signal']).clip(0, 1)}
    def generate_signals_dynamic(self, data, params): r = self.calculate(data, params); entries, exits = (r['rvi'] > r['signal']) & (r['rvi'].shift(1) <= r['signal'].shift(1)), (r['rvi'] < r['signal']) & (r['rvi'].shift(1) >= r['signal'].shift(1)); return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('rvi_cross', index=data.index), 'signal_strength': abs(r['rvi'] - r['signal']).clip(0, 1)}
    def get_ml_features(self, data, params): r = self.calculate(data, params); return pd.DataFrame({'rvi': r['rvi'], 'rvi_signal': r['signal'], 'rvi_divergence': r['rvi'] - r['signal']}, index=data.index)
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0): s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params); return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'], tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
