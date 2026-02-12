"""173 - Weekly Range"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_WeeklyRange:
    """Weekly Range - Multi-Day Range Analysis"""
    PARAMETERS = {
        'week_bars': {'default': 48, 'values': [24,48,96], 'optimize': False},
        'period': {'default': 4, 'values': [2,3,4,5,8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "WeeklyRange", "Range", __version__
    
    def calculate(self, data, params):
        week_bars = params.get('week_bars', 48)
        period = params.get('period', 4)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Weekly high/low (rolling window)
        weekly_high = high.rolling(week_bars).max()
        weekly_low = low.rolling(week_bars).min()
        
        # Weekly Range
        weekly_range = weekly_high - weekly_low
        
        # Average Weekly Range
        avg_weekly_range = weekly_range.rolling(period).mean()
        
        # Range as % of price
        range_percent = (weekly_range / close) * 100
        
        # Position in weekly range
        range_position = (close - weekly_low) / (weekly_range + 1e-10)
        
        # Range expansion
        range_expanding = (weekly_range > avg_weekly_range).astype(int)
        
        # Breakout signals
        upper_breakout = (close > weekly_high.shift(1)).astype(int)
        lower_breakout = (close < weekly_low.shift(1)).astype(int)
        
        return pd.DataFrame({
            'weekly_high': weekly_high,
            'weekly_low': weekly_low,
            'weekly_range': weekly_range,
            'avg_weekly_range': avg_weekly_range,
            'range_percent': range_percent,
            'range_position': range_position,
            'range_expanding': range_expanding,
            'upper_breakout': upper_breakout,
            'lower_breakout': lower_breakout
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        range_data = self.calculate(data, params)
        # Entry on upper breakout
        entries = (range_data['upper_breakout'] == 1)
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
        entries = (range_data['upper_breakout'] == 1)
        exits = (range_data['range_position'] < 0.3)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('range_reversion', index=data.index),
                'signal_strength': range_data['range_position']}
    
    def get_ml_features(self, data, params):
        range_data = self.calculate(data, params)
        return pd.DataFrame({
            'range_percent': range_data['range_percent'],
            'range_position': range_data['range_position'],
            'range_expanding': range_data['range_expanding'],
            'upper_breakout': range_data['upper_breakout'],
            'lower_breakout': range_data['lower_breakout'],
            'range_width': range_data['weekly_range'] / range_data['avg_weekly_range']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
