"""175 - Range Expansion Index"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RangeExpansionIndex:
    """Range Expansion Index - Measures Range Growth"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23], 'optimize': True},
        'threshold': {'default': 50, 'values': [30,40,50,60,70], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RangeExpansionIndex", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Current range
        current_range = high - low
        
        # Range N periods ago
        range_ago = current_range.shift(period)
        
        # Range Expansion Index (REI)
        # Percentage of bars where current range > range N periods ago
        range_expanded = (current_range > range_ago).astype(int)
        rei = range_expanded.rolling(period).sum() / period * 100
        
        # Range momentum
        range_momentum = current_range - current_range.rolling(period).mean()
        
        # Range acceleration
        range_acceleration = range_momentum.diff()
        
        # Expansion strength
        expansion_strength = (current_range / (range_ago + 1e-10) - 1) * 100
        
        # Average expansion strength
        avg_expansion = expansion_strength.rolling(period).mean()
        
        return pd.DataFrame({
            'rei': rei,
            'range_momentum': range_momentum,
            'range_acceleration': range_acceleration,
            'expansion_strength': expansion_strength,
            'avg_expansion': avg_expansion,
            'expanding': range_expanded
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        rei_data = self.calculate(data, params)
        threshold = params.get('threshold', 50)
        # Entry when REI crosses above threshold (expansion phase)
        # Lockerere Entry-Bedingung: REI > 40
        entries = (rei_data['rei'] > 40) & (rei_data['rei'].shift(1) <= 40)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (rei_data['rei'] / 100).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        rei_data = self.calculate(data, params)
        threshold = params.get('threshold', 50)
        # Lockerere Entry-Bedingung: REI > 40
        entries = (rei_data['rei'] > 40) & (rei_data['rei'].shift(1) <= 40)
        exits = (rei_data['rei'] < 100 - threshold) & (rei_data['rei'].shift(1) >= 100 - threshold)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('range_contraction', index=data.index),
                'signal_strength': (rei_data['rei'] / 100).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        rei_data = self.calculate(data, params)
        return pd.DataFrame({
            'rei': rei_data['rei'],
            'range_momentum': rei_data['range_momentum'],
            'range_acceleration': rei_data['range_acceleration'],
            'expansion_strength': rei_data['expansion_strength'],
            'expanding': rei_data['expanding'],
            'rei_slope': rei_data['rei'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
