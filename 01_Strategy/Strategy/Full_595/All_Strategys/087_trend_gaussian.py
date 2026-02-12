"""087 - Gaussian Filter"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Gaussian:
    """Gaussian Filter - Smooth Moving Average"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23], 'optimize': True},
        'poles': {'default': 4, 'values': [2,3,4,5,6], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Gaussian", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        poles = params.get('poles', 4)
        
        # Beta and Alpha
        beta = (1 - np.cos(2 * np.pi / period)) / (np.power(2, 1/poles) - 1)
        alpha = -beta + np.sqrt(beta * beta + 2 * beta)
        
        # Coefficients
        a = np.power(alpha, poles)
        
        # Gaussian filter
        gaussian = pd.Series(index=data.index, dtype=float)
        gaussian.iloc[0] = data['close'].iloc[0]
        
        for i in range(1, len(data)):
            gaussian.iloc[i] = a * data['close'].iloc[i] + (1 - a) * gaussian.iloc[i-1]
        
        return gaussian.fillna(data['close'])
    
    def generate_signals_fixed(self, data, params):
        gaussian = self.calculate(data, params)
        # Entry when price crosses above Gaussian
        entries = (data['close'] > gaussian) & (data['close'].shift(1) <= gaussian.shift(1))
        
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
                'signal_strength': abs(data['close'] - gaussian) / (gaussian + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        gaussian = self.calculate(data, params)
        entries = (data['close'] > gaussian) & (data['close'].shift(1) <= gaussian.shift(1))
        exits = (data['close'] < gaussian) & (data['close'].shift(1) >= gaussian.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('gaussian_cross', index=data.index),
                'signal_strength': abs(data['close'] - gaussian) / (gaussian + 1e-10)}
    
    def get_ml_features(self, data, params):
        gaussian = self.calculate(data, params)
        return pd.DataFrame({'gaussian_value': gaussian, 'gaussian_slope': gaussian.diff(),
                           'price_above_gaussian': (data['close'] > gaussian).astype(int),
                           'distance_from_gaussian': data['close'] - gaussian}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
