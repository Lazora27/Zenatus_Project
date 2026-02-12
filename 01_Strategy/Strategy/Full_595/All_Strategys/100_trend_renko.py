"""100 - Renko Trend Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RenkoTrend:
    """Renko Trend - Simplified Renko-based Trend Detection"""
    PARAMETERS = {
        'brick_size': {'default': 0.001, 'values': [0.0005,0.001,0.0015,0.002,0.003], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RenkoTrend", "Trend", __version__
    
    def calculate(self, data, params):
        brick_size = params.get('brick_size', 0.001)
        
        # Simplified Renko Trend
        renko_trend = pd.Series(0, index=data.index)
        last_brick = data['close'].iloc[0]
        
        for i in range(1, len(data)):
            price = data['close'].iloc[i]
            
            # Check for upward brick
            if price >= last_brick + brick_size:
                renko_trend.iloc[i] = 1
                last_brick = last_brick + brick_size
            # Check for downward brick
            elif price <= last_brick - brick_size:
                renko_trend.iloc[i] = -1
                last_brick = last_brick - brick_size
            else:
                renko_trend.iloc[i] = renko_trend.iloc[i-1]
        
        return renko_trend
    
    def generate_signals_fixed(self, data, params):
        renko = self.calculate(data, params)
        # Entry when trend changes to up
        entries = (renko == 1) & (renko.shift(1) <= 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(renko)}
    
    def generate_signals_dynamic(self, data, params):
        renko = self.calculate(data, params)
        entries = (renko == 1) & (renko.shift(1) <= 0)
        exits = (renko == -1) & (renko.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('renko_reverse', index=data.index),
                'signal_strength': abs(renko)}
    
    def get_ml_features(self, data, params):
        renko = self.calculate(data, params)
        return pd.DataFrame({'renko_trend': renko,
                           'renko_uptrend': (renko == 1).astype(int),
                           'renko_downtrend': (renko == -1).astype(int),
                           'renko_neutral': (renko == 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
