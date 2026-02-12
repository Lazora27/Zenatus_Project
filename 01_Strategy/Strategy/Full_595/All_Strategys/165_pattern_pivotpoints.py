"""165 - Pivot Points (Classic, Fibonacci, Camarilla)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PivotPoints:
    """Pivot Points - Multiple pivot calculation methods"""
    PARAMETERS = {
        'method': {'default': 'classic', 'values': ['classic', 'fibonacci', 'camarilla'], 'optimize': True},
        'proximity': {'default': 0.002, 'values': [0.001,0.002,0.003], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PivotPoints", "Pattern", __version__
    
    def calculate(self, data, params):
        method = params.get('method', 'classic')
        proximity = params.get('proximity', 0.002)
        
        # Calculate daily pivots (using rolling window as proxy)
        period = 24  # Assume 30-min bars, 24 bars = 12 hours
        
        high_d = data['high'].rolling(period).max()
        low_d = data['low'].rolling(period).min()
        close_d = data['close'].shift(period)
        
        # Pivot Point
        pp = (high_d + low_d + close_d) / 3
        
        if method == 'classic':
            # Classic Pivot Points
            r1 = 2 * pp - low_d
            s1 = 2 * pp - high_d
            r2 = pp + (high_d - low_d)
            s2 = pp - (high_d - low_d)
            r3 = high_d + 2 * (pp - low_d)
            s3 = low_d - 2 * (high_d - pp)
            
        elif method == 'fibonacci':
            # Fibonacci Pivot Points
            range_d = high_d - low_d
            r1 = pp + 0.382 * range_d
            s1 = pp - 0.382 * range_d
            r2 = pp + 0.618 * range_d
            s2 = pp - 0.618 * range_d
            r3 = pp + 1.000 * range_d
            s3 = pp - 1.000 * range_d
            
        else:  # camarilla
            # Camarilla Pivot Points
            range_d = high_d - low_d
            r1 = close_d + range_d * 1.1 / 12
            s1 = close_d - range_d * 1.1 / 12
            r2 = close_d + range_d * 1.1 / 6
            s2 = close_d - range_d * 1.1 / 6
            r3 = close_d + range_d * 1.1 / 4
            s3 = close_d - range_d * 1.1 / 4
        
        # Check proximity to levels
        near_pp = abs(data['close'] - pp) / data['close'] < proximity
        near_r1 = abs(data['close'] - r1) / data['close'] < proximity
        near_s1 = abs(data['close'] - s1) / data['close'] < proximity
        near_r2 = abs(data['close'] - r2) / data['close'] < proximity
        near_s2 = abs(data['close'] - s2) / data['close'] < proximity
        
        # Signal
        signal = pd.Series(0, index=data.index)
        signal[near_s1 | near_s2] = 1  # Near support
        signal[near_r1 | near_r2] = -1  # Near resistance
        signal[near_pp] = 0  # At pivot
        
        return pd.DataFrame({
            'signal': signal,
            'pp': pp.fillna(data['close']),
            'r1': r1.fillna(data['close']),
            's1': s1.fillna(data['close']),
            'r2': r2.fillna(data['close']),
            's2': s2.fillna(data['close']),
            'r3': r3.fillna(data['close']),
            's3': s3.fillna(data['close'])
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        pivots = self.calculate(data, params)
        # Entry near support levels
        entries = (pivots['signal'] == 1)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(pivots['signal'])}
    
    def generate_signals_dynamic(self, data, params):
        pivots = self.calculate(data, params)
        entries = (pivots['signal'] == 1)
        exits = (pivots['signal'] == -1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('near_resistance', index=data.index),
                'signal_strength': abs(pivots['signal'])}
    
    def get_ml_features(self, data, params):
        pivots = self.calculate(data, params)
        return pd.DataFrame({
            'pivot_signal': pivots['signal'],
            'pivot_dist_pp': (data['close'] - pivots['pp']) / data['close'],
            'pivot_dist_r1': (pivots['r1'] - data['close']) / data['close'],
            'pivot_dist_s1': (data['close'] - pivots['s1']) / data['close'],
            'pivot_near_support': (pivots['signal'] == 1).astype(int),
            'pivot_near_resistance': (pivots['signal'] == -1).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
