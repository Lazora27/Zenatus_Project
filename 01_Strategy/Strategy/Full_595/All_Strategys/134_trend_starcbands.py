"""134 - STARC Bands"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_STARCBands:
    """STARC Bands - Stoller Average Range Channels"""
    PARAMETERS = {
        'ma_period': {'default': 5, 'values': [3,5,7,10], 'optimize': True},
        'atr_period': {'default': 15, 'values': [10,14,15,20], 'optimize': True},
        'atr_mult': {'default': 2.0, 'values': [1.0,1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "STARCBands", "Volatility", __version__
    
    def calculate(self, data, params):
        ma_period = params.get('ma_period', 5)
        atr_period = params.get('atr_period', 15)
        atr_mult = params.get('atr_mult', 2.0)
        
        # Simple Moving Average
        sma = data['close'].rolling(ma_period).mean()
        
        # Average True Range
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()
        
        # STARC Bands
        upper = sma + (atr * atr_mult)
        lower = sma - (atr * atr_mult)
        
        return pd.DataFrame({
            'upper': upper.fillna(data['close']),
            'middle': sma.fillna(data['close']),
            'lower': lower.fillna(data['close']),
            'atr': atr.fillna(0)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        bands = self.calculate(data, params)
        # Entry when price crosses above middle
        entries = (data['close'] > bands['middle']) & (data['close'].shift(1) <= bands['middle'].shift(1))
        
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
                'signal_strength': (data['close'] - bands['lower']) / (bands['upper'] - bands['lower'] + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        bands = self.calculate(data, params)
        entries = (data['close'] > bands['middle']) & (data['close'].shift(1) <= bands['middle'].shift(1))
        exits = (data['close'] < bands['middle']) & (data['close'].shift(1) >= bands['middle'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('starc_cross', index=data.index),
                'signal_strength': (data['close'] - bands['lower']) / (bands['upper'] - bands['lower'] + 1e-10)}
    
    def get_ml_features(self, data, params):
        bands = self.calculate(data, params)
        return pd.DataFrame({
            'starc_upper': bands['upper'],
            'starc_middle': bands['middle'],
            'starc_lower': bands['lower'],
            'starc_atr': bands['atr'],
            'starc_position': (data['close'] - bands['lower']) / (bands['upper'] - bands['lower'] + 1e-10),
            'starc_width': bands['upper'] - bands['lower']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
