"""171 - True Range"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TrueRange:
    """True Range - Maximum of High-Low, High-Close, Low-Close"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23], 'optimize': True},
        'threshold': {'default': 1.5, 'values': [1.0,1.2,1.5,1.8,2.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TrueRange", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close = data['high'], data['low'], data['close']
        
        # True Range components
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        # True Range (max of three)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Average True Range
        atr = tr.rolling(period).mean()
        
        # True Range as % of price
        tr_percent = (tr / close) * 100
        
        # TR percentile rank
        tr_rank = tr.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # TR expansion/contraction
        tr_ma = tr.rolling(period).mean()
        tr_expanding = (tr > tr_ma).astype(int)
        
        return pd.DataFrame({
            'tr': tr,
            'atr': atr,
            'tr_percent': tr_percent,
            'tr_rank': tr_rank,
            'tr_expanding': tr_expanding
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        tr_data = self.calculate(data, params)
        threshold = params.get('threshold', 1.5)
        # Entry when TR expands above threshold
        entries = (tr_data['tr'] > tr_data['atr'] * threshold) & (tr_data['tr'].shift(1) <= tr_data['atr'].shift(1) * threshold)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': tr_data['tr_rank']}
    
    def generate_signals_dynamic(self, data, params):
        tr_data = self.calculate(data, params)
        threshold = params.get('threshold', 1.5)
        entries = (tr_data['tr'] > tr_data['atr'] * threshold) & (tr_data['tr'].shift(1) <= tr_data['atr'].shift(1) * threshold)
        exits = (tr_data['tr'] < tr_data['atr']) & (tr_data['tr'].shift(1) >= tr_data['atr'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('tr_contraction', index=data.index),
                'signal_strength': tr_data['tr_rank']}
    
    def get_ml_features(self, data, params):
        tr_data = self.calculate(data, params)
        return pd.DataFrame({
            'tr': tr_data['tr'],
            'tr_percent': tr_data['tr_percent'],
            'tr_rank': tr_data['tr_rank'],
            'tr_expanding': tr_data['tr_expanding'],
            'tr_slope': tr_data['tr'].diff(),
            'tr_normalized': tr_data['tr'] / tr_data['atr']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
