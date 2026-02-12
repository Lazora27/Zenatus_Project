"""108 - Decycler"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Decycler:
    """Decycler - Ehlers' high-pass filter"""
    PARAMETERS = {
        'hp_period': {'default': 125, 'values': [50,100,125,150,200], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Decycler", "Trend", __version__
    
    def calculate(self, data, params):
        hp_period = params.get('hp_period', 125)
        
        # High-pass filter coefficient
        alpha1 = (np.cos(0.707 * 2 * np.pi / hp_period) + np.sin(0.707 * 2 * np.pi / hp_period) - 1) / \
                np.cos(0.707 * 2 * np.pi / hp_period)
        
        # High-pass filter
        hp = pd.Series(0.0, index=data.index)
        
        for i in range(2, len(data)):
            hp.iloc[i] = (1 - alpha1 / 2) ** 2 * (data['close'].iloc[i] - 2 * data['close'].iloc[i-1] + 
                        data['close'].iloc[i-2]) + 2 * (1 - alpha1) * hp.iloc[i-1] - (1 - alpha1) ** 2 * hp.iloc[i-2]
        
        # Decycler = Price - High-pass filter
        decycler = data['close'] - hp
        
        return decycler.fillna(data['close'])
    
    def generate_signals_fixed(self, data, params):
        decycler = self.calculate(data, params)
        # Entry when price crosses above decycler
        entries = (data['close'] > decycler) & (data['close'].shift(1) <= decycler.shift(1))
        
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
                'signal_strength': abs(data['close'] - decycler) / (decycler + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        decycler = self.calculate(data, params)
        entries = (data['close'] > decycler) & (data['close'].shift(1) <= decycler.shift(1))
        exits = (data['close'] < decycler) & (data['close'].shift(1) >= decycler.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('decycler_cross', index=data.index),
                'signal_strength': abs(data['close'] - decycler) / (decycler + 1e-10)}
    
    def get_ml_features(self, data, params):
        decycler = self.calculate(data, params)
        return pd.DataFrame({'decycler_value': decycler, 'decycler_slope': decycler.diff(),
                           'price_above_decycler': (data['close'] > decycler).astype(int),
                           'distance_from_decycler': data['close'] - decycler}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
