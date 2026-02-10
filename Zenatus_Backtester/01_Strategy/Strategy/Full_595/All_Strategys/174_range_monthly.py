"""174 - Monthly Range"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MonthlyRange:
    """Monthly Range - Long-Term Range Analysis"""
    PARAMETERS = {
        'month_bars': {'default': 240, 'values': [120,240,480], 'optimize': False},
        'period': {'default': 3, 'values': [2,3,4,6], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MonthlyRange", "Range", __version__
    
    def calculate(self, data, params):
        month_bars = params.get('month_bars', 240)
        period = params.get('period', 3)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Monthly high/low
        monthly_high = high.rolling(month_bars).max()
        monthly_low = low.rolling(month_bars).min()
        
        # Monthly Range
        monthly_range = monthly_high - monthly_low
        
        # Average Monthly Range
        avg_monthly_range = monthly_range.rolling(period).mean()
        
        # Range as % of price
        range_percent = (monthly_range / close) * 100
        
        # Position in monthly range (0-1)
        range_position = (close - monthly_low) / (monthly_range + 1e-10)
        
        # Range quartiles
        range_q1 = monthly_low + monthly_range * 0.25
        range_q2 = monthly_low + monthly_range * 0.50
        range_q3 = monthly_low + monthly_range * 0.75
        
        # Current quartile
        in_q1 = (close <= range_q1).astype(int)
        in_q2 = ((close > range_q1) & (close <= range_q2)).astype(int)
        in_q3 = ((close > range_q2) & (close <= range_q3)).astype(int)
        in_q4 = (close > range_q3).astype(int)
        
        return pd.DataFrame({
            'monthly_high': monthly_high,
            'monthly_low': monthly_low,
            'monthly_range': monthly_range,
            'range_percent': range_percent,
            'range_position': range_position,
            'in_q1': in_q1,
            'in_q2': in_q2,
            'in_q3': in_q3,
            'in_q4': in_q4
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        range_data = self.calculate(data, params)
        # Entry when price in lower quartile (Q1) and rising
        entries = (range_data['in_q1'] == 1) & (data['close'] > data['close'].shift(1))
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
        entries = (range_data['in_q1'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (range_data['in_q4'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('upper_quartile', index=data.index),
                'signal_strength': range_data['range_position']}
    
    def get_ml_features(self, data, params):
        range_data = self.calculate(data, params)
        return pd.DataFrame({
            'range_percent': range_data['range_percent'],
            'range_position': range_data['range_position'],
            'in_q1': range_data['in_q1'],
            'in_q2': range_data['in_q2'],
            'in_q3': range_data['in_q3'],
            'in_q4': range_data['in_q4']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
