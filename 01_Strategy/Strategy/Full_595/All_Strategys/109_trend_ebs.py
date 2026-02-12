"""109 - Even Better Sinewave"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_EvenBetterSinewave:
    """Even Better Sinewave - Ehlers' cycle indicator"""
    PARAMETERS = {
        'hp_period': {'default': 40, 'values': [20,30,40,50,60], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "EvenBetterSinewave", "Cycle", __version__
    
    def calculate(self, data, params):
        hp_period = params.get('hp_period', 40)
        
        # High-pass filter
        alpha1 = (1 - np.sin(2 * np.pi / hp_period)) / np.cos(2 * np.pi / hp_period)
        
        hp = pd.Series(0.0, index=data.index)
        for i in range(1, len(data)):
            hp.iloc[i] = 0.5 * (1 + alpha1) * (data['close'].iloc[i] - data['close'].iloc[i-1]) + alpha1 * hp.iloc[i-1]
        
        # Compute Filter
        filt = pd.Series(0.0, index=data.index)
        for i in range(2, len(data)):
            filt.iloc[i] = 0.5 * hp.iloc[i] + 0.5 * hp.iloc[i-1]
        
        # Compute Wave
        wave = pd.Series(0.0, index=data.index)
        for i in range(3, len(data)):
            wave.iloc[i] = (filt.iloc[i] + filt.iloc[i-1] + filt.iloc[i-2]) / 3
        
        # Compute Power
        pwr = pd.Series(0.0, index=data.index)
        for i in range(2, len(data)):
            pwr.iloc[i] = (filt.iloc[i] ** 2 + filt.iloc[i-1] ** 2 + filt.iloc[i-2] ** 2) / 3
        
        # Even Better Sinewave
        ebs = wave / (np.sqrt(pwr) + 1e-10)
        
        return ebs.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ebs = self.calculate(data, params)
        # Entry when EBS crosses above 0
        entries = (ebs > 0) & (ebs.shift(1) <= 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(ebs).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        ebs = self.calculate(data, params)
        entries = (ebs > 0) & (ebs.shift(1) <= 0)
        exits = (ebs < 0) & (ebs.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('ebs_cross', index=data.index),
                'signal_strength': abs(ebs).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        ebs = self.calculate(data, params)
        return pd.DataFrame({'ebs_value': ebs, 'ebs_slope': ebs.diff(),
                           'ebs_positive': (ebs > 0).astype(int),
                           'ebs_extreme': (abs(ebs) > 0.7).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
