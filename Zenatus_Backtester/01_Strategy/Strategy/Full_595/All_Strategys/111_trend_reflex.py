"""111 - Reflex Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Reflex:
    """Reflex Indicator - Ehlers' slope indicator"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Reflex", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Super Smoother Filter
        a1 = np.exp(-1.414 * np.pi / period)
        b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
        c2 = b1
        c3 = -a1 * a1
        c1 = 1 - c2 - c3
        
        filt = pd.Series(0.0, index=data.index)
        for i in range(2, len(data)):
            filt.iloc[i] = c1 * (data['close'].iloc[i] + data['close'].iloc[i-1]) / 2 + \
                          c2 * filt.iloc[i-1] + c3 * filt.iloc[i-2]
        
        # Calculate slope
        slope = pd.Series(0.0, index=data.index)
        for i in range(period, len(data)):
            sum_x = 0
            sum_y = 0
            sum_xx = 0
            sum_xy = 0
            
            for count in range(period):
                x = count
                y = filt.iloc[i - count]
                sum_x += x
                sum_y += y
                sum_xx += x * x
                sum_xy += x * y
            
            if period * sum_xx - sum_x * sum_x != 0:
                slope.iloc[i] = (period * sum_xy - sum_x * sum_y) / (period * sum_xx - sum_x * sum_x)
        
        # Reflex = Sum of slopes
        reflex = slope.rolling(period).sum()
        
        return reflex.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        reflex = self.calculate(data, params)
        # Entry when reflex crosses above 0
        entries = (reflex > 0) & (reflex.shift(1) <= 0)
        
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
                'signal_strength': abs(reflex).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        reflex = self.calculate(data, params)
        entries = (reflex > 0) & (reflex.shift(1) <= 0)
        exits = (reflex < 0) & (reflex.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('reflex_cross', index=data.index),
                'signal_strength': abs(reflex).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        reflex = self.calculate(data, params)
        return pd.DataFrame({'reflex_value': reflex, 'reflex_slope': reflex.diff(),
                           'reflex_positive': (reflex > 0).astype(int),
                           'reflex_acceleration': reflex.diff().diff()}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
