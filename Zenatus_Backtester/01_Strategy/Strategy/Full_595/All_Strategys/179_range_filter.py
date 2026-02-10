"""179 - Range Filter"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RangeFilter:
    """Range Filter - Smoothed Range-Based Trend Filter"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [13,17,19,20,21,23,25,29], 'optimize': True},
        'multiplier': {'default': 1.5, 'values': [1.0,1.2,1.5,1.8,2.0,2.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RangeFilter", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        multiplier = params.get('multiplier', 1.5)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Range calculation
        current_range = high - low
        smooth_range = current_range.ewm(span=period).mean()
        
        # Range filter (price +/- range)
        range_filter = close.copy()
        upward = pd.Series(True, index=data.index)
        
        for i in range(1, len(data)):
            if upward.iloc[i-1]:
                # Uptrend: filter is close - range
                range_filter.iloc[i] = max(range_filter.iloc[i-1], 
                                          close.iloc[i] - smooth_range.iloc[i] * multiplier)
                if close.iloc[i] < range_filter.iloc[i]:
                    upward.iloc[i] = False
                    range_filter.iloc[i] = close.iloc[i] + smooth_range.iloc[i] * multiplier
            else:
                # Downtrend: filter is close + range
                range_filter.iloc[i] = min(range_filter.iloc[i-1],
                                          close.iloc[i] + smooth_range.iloc[i] * multiplier)
                if close.iloc[i] > range_filter.iloc[i]:
                    upward.iloc[i] = True
                    range_filter.iloc[i] = close.iloc[i] - smooth_range.iloc[i] * multiplier
        
        # Trend direction
        trend_up = upward.astype(int)
        trend_change = trend_up.diff().abs()
        
        # Distance from filter
        distance = close - range_filter
        distance_percent = distance / close * 100
        
        return pd.DataFrame({
            'range_filter': range_filter,
            'smooth_range': smooth_range,
            'trend_up': trend_up,
            'trend_change': trend_change,
            'distance': distance,
            'distance_percent': distance_percent
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        filter_data = self.calculate(data, params)
        # Entry on trend change to upward
        entries = (filter_data['trend_change'] == 1) & (filter_data['trend_up'] == 1)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': filter_data['trend_up'].astype(float)}
    
    def generate_signals_dynamic(self, data, params):
        filter_data = self.calculate(data, params)
        entries = (filter_data['trend_change'] == 1) & (filter_data['trend_up'] == 1)
        exits = (filter_data['trend_change'] == 1) & (filter_data['trend_up'] == 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('trend_reversal', index=data.index),
                'signal_strength': filter_data['trend_up'].astype(float)}
    
    def get_ml_features(self, data, params):
        filter_data = self.calculate(data, params)
        return pd.DataFrame({
            'range_filter': filter_data['range_filter'],
            'smooth_range': filter_data['smooth_range'],
            'trend_up': filter_data['trend_up'],
            'distance_percent': filter_data['distance_percent'],
            'trend_strength': abs(filter_data['distance_percent'])
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
