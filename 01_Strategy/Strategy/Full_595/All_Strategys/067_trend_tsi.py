"""067 - TSI (True Strength Index)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"
class Indicator_TSI:
    """TSI - True Strength Index"""
    PARAMETERS = {'long': {'default': 25, 'values': [13,17,19,21,23,25,29,31,34], 'optimize': True}, 'short': {'default': 13, 'values': [5,7,8,11,13,14,17,19], 'optimize': True}, 'signal': {'default': 7, 'values': [3,5,7,8,11], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category, self.version = "TSI", "Momentum", __version__
    def calculate(self, data, params): long, short, sig = params.get('long', 25), params.get('short', 13), params.get('signal', 7); pc = data['close'].diff(); double_smoothed_pc = pc.ewm(span=long).mean().ewm(span=short).mean(); double_smoothed_abs_pc = abs(pc).ewm(span=long).mean().ewm(span=short).mean(); tsi = 100 * (double_smoothed_pc / (double_smoothed_abs_pc + 1e-10)); signal = tsi.ewm(span=sig).mean(); return pd.DataFrame({'tsi': tsi.fillna(0), 'signal': signal.fillna(0)}, index=data.index)
    def generate_signals_fixed(self, data, params):
        r = self.calculate(data, params)
        entries = (r['tsi'] > r['signal']) & (r['tsi'].shift(1) <= r['signal'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(r['tsi']).clip(0, 100) / 100}
    def generate_signals_dynamic(self, data, params): r = self.calculate(data, params); entries, exits = (r['tsi'] > r['signal']) & (r['tsi'].shift(1) <= r['signal'].shift(1)), (r['tsi'] < r['signal']) & (r['tsi'].shift(1) >= r['signal'].shift(1)); return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('tsi_cross', index=data.index), 'signal_strength': abs(r['tsi']).clip(0, 100) / 100}
    def get_ml_features(self, data, params): r = self.calculate(data, params); return pd.DataFrame({'tsi': r['tsi'], 'tsi_signal': r['signal'], 'tsi_divergence': r['tsi'] - r['signal']}, index=data.index)
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0): s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params); return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'], tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
