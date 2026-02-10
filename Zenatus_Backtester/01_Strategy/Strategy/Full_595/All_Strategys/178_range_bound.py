"""178 - Range Bound"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RangeBound:
    """Range Bound - Identifies Range-Bound Markets"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [13,17,19,20,21,23,25,29], 'optimize': True},
        'threshold': {'default': 0.02, 'values': [0.01,0.015,0.02,0.025,0.03], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RangeBound", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 0.02)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Range boundaries
        range_high = high.rolling(period).max()
        range_low = low.rolling(period).min()
        range_size = range_high - range_low
        
        # Range as % of price
        range_percent = range_size / close
        
        # Range-bound detection (narrow range)
        is_range_bound = (range_percent < threshold).astype(int)
        
        # Range-bound duration
        range_bound_duration = is_range_bound.rolling(period).sum()
        
        # Price position in range
        range_position = (close - range_low) / (range_size + 1e-10)
        
        # Range stability (low volatility)
        range_stability = 1 - (range_size.rolling(period).std() / (range_size.rolling(period).mean() + 1e-10))
        
        # Mean reversion signals
        oversold = (range_position < 0.2).astype(int)
        overbought = (range_position > 0.8).astype(int)
        
        return pd.DataFrame({
            'range_high': range_high,
            'range_low': range_low,
            'range_percent': range_percent,
            'is_range_bound': is_range_bound,
            'range_bound_duration': range_bound_duration,
            'range_position': range_position,
            'range_stability': range_stability,
            'oversold': oversold,
            'overbought': overbought
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        range_data = self.calculate(data, params)
        # Entry when range-bound and oversold
        entries = (range_data['is_range_bound'] == 1) & (range_data['oversold'] == 1)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': range_data['range_position']}
    
    def generate_signals_dynamic(self, data, params):
        range_data = self.calculate(data, params)
        entries = (range_data['is_range_bound'] == 1) & (range_data['oversold'] == 1)
        exits = (range_data['overbought'] == 1) | (range_data['is_range_bound'] == 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('range_exit', index=data.index),
                'signal_strength': range_data['range_position']}
    
    def get_ml_features(self, data, params):
        range_data = self.calculate(data, params)
        return pd.DataFrame({
            'range_percent': range_data['range_percent'],
            'is_range_bound': range_data['is_range_bound'],
            'range_bound_duration': range_data['range_bound_duration'],
            'range_position': range_data['range_position'],
            'range_stability': range_data['range_stability'],
            'oversold': range_data['oversold'],
            'overbought': range_data['overbought']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
