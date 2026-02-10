"""137 - ATR Channels"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ATRChannels:
    """ATR Channels - Moving average with ATR-based bands"""
    PARAMETERS = {
        'ma_period': {'default': 20, 'values': [10,14,20,25,30], 'optimize': True},
        'atr_period': {'default': 14, 'values': [10,14,20,25], 'optimize': True},
        'atr_mult': {'default': 2.0, 'values': [1.0,1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ATRChannels", "Volatility", __version__
    
    def calculate(self, data, params):
        ma_period = params.get('ma_period', 20)
        atr_period = params.get('atr_period', 14)
        atr_mult = params.get('atr_mult', 2.0)
        
        # Moving average
        ma = data['close'].rolling(ma_period).mean()
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()
        
        # Channels
        upper = ma + (atr * atr_mult)
        lower = ma - (atr * atr_mult)
        
        return pd.DataFrame({
            'upper': upper.fillna(data['close']),
            'middle': ma.fillna(data['close']),
            'lower': lower.fillna(data['close']),
            'atr': atr.fillna(0)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        channels = self.calculate(data, params)
        # Entry when price crosses above MA
        entries = (data['close'] > channels['middle']) & (data['close'].shift(1) <= channels['middle'].shift(1))
        
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
                'signal_strength': (data['close'] - channels['lower']) / (channels['upper'] - channels['lower'] + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        channels = self.calculate(data, params)
        entries = (data['close'] > channels['middle']) & (data['close'].shift(1) <= channels['middle'].shift(1))
        exits = (data['close'] < channels['middle']) & (data['close'].shift(1) >= channels['middle'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('atr_cross', index=data.index),
                'signal_strength': (data['close'] - channels['lower']) / (channels['upper'] - channels['lower'] + 1e-10)}
    
    def get_ml_features(self, data, params):
        channels = self.calculate(data, params)
        return pd.DataFrame({
            'atr_upper': channels['upper'],
            'atr_middle': channels['middle'],
            'atr_lower': channels['lower'],
            'atr_value': channels['atr'],
            'atr_position': (data['close'] - channels['lower']) / (channels['upper'] - channels['lower'] + 1e-10),
            'atr_width': channels['upper'] - channels['lower']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
