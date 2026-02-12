"""133 - Acceleration Bands"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AccelerationBands:
    """Acceleration Bands - Price envelope with acceleration factor"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30], 'optimize': True},
        'factor': {'default': 0.001, 'values': [0.0005,0.001,0.002,0.003], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AccelerationBands", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        factor = params.get('factor', 0.001)
        
        # Simple Moving Average
        sma = data['close'].rolling(period).mean()
        
        # High-Low range
        hl_range = data['high'] - data['low']
        
        # Acceleration factor
        upper = data['high'] * (1 + factor * (hl_range / data['close']))
        lower = data['low'] * (1 - factor * (hl_range / data['close']))
        
        # Smooth the bands
        upper_band = upper.rolling(period).mean()
        lower_band = lower.rolling(period).mean()
        
        return pd.DataFrame({
            'upper': upper_band.fillna(data['close']),
            'middle': sma.fillna(data['close']),
            'lower': lower_band.fillna(data['close'])
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
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('acc_cross', index=data.index),
                'signal_strength': (data['close'] - bands['lower']) / (bands['upper'] - bands['lower'] + 1e-10)}
    
    def get_ml_features(self, data, params):
        bands = self.calculate(data, params)
        return pd.DataFrame({
            'acc_upper': bands['upper'],
            'acc_middle': bands['middle'],
            'acc_lower': bands['lower'],
            'acc_position': (data['close'] - bands['lower']) / (bands['upper'] - bands['lower'] + 1e-10),
            'acc_width': bands['upper'] - bands['lower']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
