"""082 - Coppock Curve"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Coppock:
    """Coppock Curve - Long-term Momentum Indicator"""
    PARAMETERS = {
        'roc1': {'default': 14, 'values': [11,13,14,17,19,21], 'optimize': True},
        'roc2': {'default': 11, 'values': [8,10,11,13,14], 'optimize': True},
        'wma_period': {'default': 10, 'values': [5,7,8,10,11,13,14], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Coppock", "Momentum", __version__
    
    def calculate(self, data, params):
        roc1_period = params.get('roc1', 14)
        roc2_period = params.get('roc2', 11)
        wma_period = params.get('wma_period', 10)
        
        # Rate of Change
        roc1 = ((data['close'] - data['close'].shift(roc1_period)) / data['close'].shift(roc1_period) * 100).fillna(0)
        roc2 = ((data['close'] - data['close'].shift(roc2_period)) / data['close'].shift(roc2_period) * 100).fillna(0)
        
        # Sum of ROCs
        roc_sum = roc1 + roc2
        
        # WMA of sum
        weights = np.arange(1, wma_period + 1)
        coppock = roc_sum.rolling(wma_period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
        
        return coppock.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        coppock = self.calculate(data, params)
        # Entry when crosses above 0
        entries = (coppock > 0) & (coppock.shift(1) <= 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(coppock).clip(0, 10) / 10}
    
    def generate_signals_dynamic(self, data, params):
        coppock = self.calculate(data, params)
        entries = (coppock > 0) & (coppock.shift(1) <= 0)
        exits = (coppock < 0) & (coppock.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('coppock_cross', index=data.index),
                'signal_strength': abs(coppock).clip(0, 10) / 10}
    
    def get_ml_features(self, data, params):
        coppock = self.calculate(data, params)
        return pd.DataFrame({'coppock_value': coppock, 'coppock_slope': coppock.diff(),
                           'coppock_positive': (coppock > 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
