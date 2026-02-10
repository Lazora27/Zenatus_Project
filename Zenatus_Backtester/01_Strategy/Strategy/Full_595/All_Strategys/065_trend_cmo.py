"""065 - CMO (Chande Momentum Oscillator)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"
class Indicator_CMO:
    """CMO - Chande Momentum Oscillator"""
    PARAMETERS = {'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23,29,31,34,37,41,43,47], 'optimize': True}, 'overbought': {'default': 50, 'values': [40,45,50,55,60], 'optimize': True}, 'oversold': {'default': -50, 'values': [-60,-55,-50,-45,-40], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category, self.version = "CMO", "Momentum", __version__
    def calculate(self, data, params): period = params.get('period', 14); delta = data['close'].diff(); gain, loss = delta.where(delta > 0, 0), -delta.where(delta < 0, 0); sum_gain, sum_loss = gain.rolling(period).sum(), loss.rolling(period).sum(); return ((sum_gain - sum_loss) / (sum_gain + sum_loss + 1e-10)) * 100
    def generate_signals_fixed(self, data, params):
        cmo = self.calculate(data, params).fillna(0); oversold = params.get('oversold', -50); entries = (cmo > oversold) & (cmo.shift(1) <= oversold); tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001; exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos: in_pos, ep = True, data['close'].iloc[i]; tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l): exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index), 'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(cmo).clip(0, 100) / 100}
    def generate_signals_dynamic(self, data, params): cmo = self.calculate(data, params).fillna(0); oversold, overbought = params.get('oversold', -50), params.get('overbought', 50); entries, exits = (cmo > oversold) & (cmo.shift(1) <= oversold), (cmo < overbought) & (cmo.shift(1) >= overbought); return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cmo_cross', index=data.index), 'signal_strength': abs(cmo).clip(0, 100) / 100}
    def get_ml_features(self, data, params): cmo = self.calculate(data, params).fillna(0); return pd.DataFrame({'cmo': cmo, 'cmo_slope': cmo.diff(), 'cmo_positive': (cmo > 0).astype(int)}, index=data.index)
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0): s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params); return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'], tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
