"""139 - Dynamic Channels"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DynamicChannels:
    """Dynamic Channels - Adaptive channels with dynamic period"""
    PARAMETERS = {
        'min_period': {'default': 10, 'values': [5,10,15], 'optimize': True},
        'max_period': {'default': 50, 'values': [40,50,60], 'optimize': True},
        'mult': {'default': 2.0, 'values': [1.0,1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DynamicChannels", "Trend", __version__
    
    def calculate(self, data, params):
        min_period = params.get('min_period', 10)
        max_period = params.get('max_period', 50)
        mult = params.get('mult', 2.0)
        
        # Calculate volatility for adaptive period
        returns = data['close'].pct_change()
        volatility = returns.rolling(20).std()
        vol_ratio = volatility / volatility.rolling(100).mean()
        
        # Adaptive period (higher vol = shorter period)
        adaptive_period = (max_period / vol_ratio).clip(min_period, max_period).fillna(20).astype(int)
        
        # Calculate dynamic MA and std
        ma = pd.Series(index=data.index, dtype=float)
        std = pd.Series(index=data.index, dtype=float)
        
        for i in range(max_period, len(data)):
            period = int(adaptive_period.iloc[i])
            ma.iloc[i] = data['close'].iloc[i-period:i].mean()
            std.iloc[i] = data['close'].iloc[i-period:i].std()
        
        # Channels
        upper = ma + (std * mult)
        lower = ma - (std * mult)
        
        return pd.DataFrame({
            'upper': upper.fillna(data['close']),
            'middle': ma.fillna(data['close']),
            'lower': lower.fillna(data['close']),
            'period': adaptive_period
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
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('dyn_cross', index=data.index),
                'signal_strength': (data['close'] - channels['lower']) / (channels['upper'] - channels['lower'] + 1e-10)}
    
    def get_ml_features(self, data, params):
        channels = self.calculate(data, params)
        return pd.DataFrame({
            'dyn_upper': channels['upper'],
            'dyn_middle': channels['middle'],
            'dyn_lower': channels['lower'],
            'dyn_period': channels['period'],
            'dyn_position': (data['close'] - channels['lower']) / (channels['upper'] - channels['lower'] + 1e-10),
            'dyn_width': channels['upper'] - channels['lower']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
