"""092 - Kauffman Efficiency Ratio Adaptive MA"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_KauffmanAMA:
    """Kauffman AMA - Adaptive Moving Average with ER"""
    PARAMETERS = {
        'er_period': {'default': 10, 'values': [5,7,8,10,11,13,14,17], 'optimize': True},
        'fast_ema': {'default': 2, 'values': [2,3,5], 'optimize': True},
        'slow_ema': {'default': 30, 'values': [20,25,30,35,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "KauffmanAMA", "Trend", __version__
    
    def calculate(self, data, params):
        er_period = params.get('er_period', 10)
        fast_ema = params.get('fast_ema', 2)
        slow_ema = params.get('slow_ema', 30)
        
        # Efficiency Ratio
        direction = abs(data['close'] - data['close'].shift(er_period))
        volatility = abs(data['close'].diff()).rolling(er_period).sum()
        er = (direction / (volatility + 1e-10)).fillna(0)
        
        # Smoothing Constants
        fast_sc = 2 / (fast_ema + 1)
        slow_sc = 2 / (slow_ema + 1)
        
        # Adaptive SC
        ssc = er * (fast_sc - slow_sc) + slow_sc
        c = ssc ** 2
        
        # KAMA
        kama = pd.Series(index=data.index, dtype=float)
        kama.iloc[0] = data['close'].iloc[0]
        
        for i in range(1, len(data)):
            kama.iloc[i] = kama.iloc[i-1] + c.iloc[i] * (data['close'].iloc[i] - kama.iloc[i-1])
        
        return kama.fillna(data['close'])
    
    def generate_signals_fixed(self, data, params):
        kama = self.calculate(data, params)
        # Entry when price crosses above KAMA
        entries = (data['close'] > kama) & (data['close'].shift(1) <= kama.shift(1))
        
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
                'signal_strength': abs(data['close'] - kama) / (kama + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        kama = self.calculate(data, params)
        entries = (data['close'] > kama) & (data['close'].shift(1) <= kama.shift(1))
        exits = (data['close'] < kama) & (data['close'].shift(1) >= kama.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('kama_cross', index=data.index),
                'signal_strength': abs(data['close'] - kama) / (kama + 1e-10)}
    
    def get_ml_features(self, data, params):
        kama = self.calculate(data, params)
        return pd.DataFrame({'kama_value': kama, 'kama_slope': kama.diff(),
                           'price_above_kama': (data['close'] > kama).astype(int),
                           'distance_from_kama': data['close'] - kama}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
