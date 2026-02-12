"""069 - Inertia Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"
class Indicator_Inertia:
    """Inertia - RVI of Linear Regression"""
    PARAMETERS = {'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29,31,34], 'optimize': True}, 'rvi_period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category, self.version = "Inertia", "Momentum", __version__
    def calculate(self, data, params): p, rvi_p = params.get('period', 20), params.get('rvi_period', 14); linreg = data['close'].rolling(p).apply(lambda x: np.polyval(np.polyfit(range(len(x)), x, 1), len(x)-1), raw=True); delta = linreg.diff(); gain, loss = delta.where(delta > 0, 0), -delta.where(delta < 0, 0); avg_gain = gain.ewm(alpha=1/rvi_p, min_periods=rvi_p).mean(); avg_loss = loss.ewm(alpha=1/rvi_p, min_periods=rvi_p).mean(); rs = avg_gain / (avg_loss + 1e-10); return (100 - (100 / (1 + rs))).fillna(50)
    def generate_signals_fixed(self, data, params):
        inertia = self.calculate(data, params)
        entries = (inertia > 50) & (inertia.shift(1) <= 50)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(inertia - 50) / 50}
    def generate_signals_dynamic(self, data, params): inertia = self.calculate(data, params); entries, exits = (inertia > 50) & (inertia.shift(1) <= 50), (inertia < 50) & (inertia.shift(1) >= 50); return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('inertia_cross', index=data.index), 'signal_strength': abs(inertia - 50) / 50}
    def get_ml_features(self, data, params): inertia = self.calculate(data, params); return pd.DataFrame({'inertia': inertia, 'inertia_slope': inertia.diff(), 'inertia_positive': (inertia > 50).astype(int)}, index=data.index)
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0): s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params); return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'], tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
