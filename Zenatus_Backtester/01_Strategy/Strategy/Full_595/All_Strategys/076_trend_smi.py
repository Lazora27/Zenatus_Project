"""076 - SMI (Stochastic Momentum Index)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SMI:
    """SMI - Stochastic Momentum Index"""
    PARAMETERS = {
        'k_period': {'default': 13, 'values': [5,7,8,11,13,14,17,19,21], 'optimize': True},
        'd_period': {'default': 25, 'values': [13,17,19,21,23,25,29,31], 'optimize': True},
        'smoothing': {'default': 3, 'values': [2,3,5,7,8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SMI", "Momentum", __version__
    
    def calculate(self, data, params):
        k_period = params.get('k_period', 13)
        d_period = params.get('d_period', 25)
        smoothing = params.get('smoothing', 3)
        
        # High/Low range
        ll = data['low'].rolling(k_period).min()
        hh = data['high'].rolling(k_period).max()
        
        # Distance from midpoint
        diff = data['close'] - (hh + ll) / 2
        rdiff = hh - ll
        
        # Double smoothed
        avgrel = diff.ewm(span=d_period).mean().ewm(span=smoothing).mean()
        avgdiff = rdiff.ewm(span=d_period).mean().ewm(span=smoothing).mean()
        
        # SMI
        smi = (avgrel / (avgdiff / 2 + 1e-10) * 100).fillna(0)
        
        # Signal line
        signal = smi.ewm(span=smoothing).mean()
        
        return pd.DataFrame({'smi': smi, 'signal': signal}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when SMI crosses above signal
        entries = (result['smi'] > result['signal']) & (result['smi'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['smi'] - result['signal']).clip(0, 100) / 100}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['smi'] > result['signal']) & (result['smi'].shift(1) <= result['signal'].shift(1))
        exits = (result['smi'] < result['signal']) & (result['smi'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('smi_cross', index=data.index),
                'signal_strength': abs(result['smi'] - result['signal']).clip(0, 100) / 100}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'smi_value': result['smi'], 'smi_signal': result['signal'],
                           'smi_divergence': result['smi'] - result['signal'],
                           'smi_overbought': (result['smi'] > 40).astype(int),
                           'smi_oversold': (result['smi'] < -40).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
