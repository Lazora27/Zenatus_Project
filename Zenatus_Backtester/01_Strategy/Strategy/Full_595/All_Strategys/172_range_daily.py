"""172 - Daily Range"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DailyRange:
    """Daily Range - High-Low Range Analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DailyRange", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        high, low, close = data['high'], data['low'], data['close']
        
        # Daily Range (High - Low)
        daily_range = high - low
        
        # Average Daily Range
        avg_range = daily_range.rolling(period).mean()
        
        # Range as % of price
        range_percent = (daily_range / close) * 100
        
        # Range percentile
        range_rank = daily_range.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Range expansion ratio
        range_ratio = daily_range / (avg_range + 1e-10)
        
        # Narrow range day (NR7 - narrowest range in 7 days)
        nr7 = daily_range == daily_range.rolling(7).min()
        
        # Wide range day
        wr7 = daily_range == daily_range.rolling(7).max()
        
        return pd.DataFrame({
            'daily_range': daily_range,
            'avg_range': avg_range,
            'range_percent': range_percent,
            'range_rank': range_rank,
            'range_ratio': range_ratio,
            'nr7': nr7.astype(int),
            'wr7': wr7.astype(int)
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        range_data = self.calculate(data, params)
        # Entry after narrow range day (NR7) - breakout setup
        entries = (range_data['nr7'].shift(1) == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': range_data['range_rank']}
    
    def generate_signals_dynamic(self, data, params):
        range_data = self.calculate(data, params)
        entries = (range_data['nr7'].shift(1) == 1) & (data['close'] > data['close'].shift(1))
        exits = (range_data['wr7'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('wide_range_day', index=data.index),
                'signal_strength': range_data['range_rank']}
    
    def get_ml_features(self, data, params):
        range_data = self.calculate(data, params)
        return pd.DataFrame({
            'range_percent': range_data['range_percent'],
            'range_rank': range_data['range_rank'],
            'range_ratio': range_data['range_ratio'],
            'nr7': range_data['nr7'],
            'wr7': range_data['wr7'],
            'range_slope': range_data['daily_range'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
