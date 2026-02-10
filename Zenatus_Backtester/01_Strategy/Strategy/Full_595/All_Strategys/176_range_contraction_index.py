"""176 - Range Contraction Index"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RangeContractionIndex:
    """Range Contraction Index - Measures Range Compression"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23], 'optimize': True},
        'threshold': {'default': 30, 'values': [20,25,30,35,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RangeContractionIndex", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close = data['high'], data['low'], data['close']
        
        current_range = high - low
        range_ago = current_range.shift(period)
        
        # Range Contraction Index (RCI)
        range_contracted = (current_range < range_ago).astype(int)
        rci = range_contracted.rolling(period).sum() / period * 100
        
        # Contraction strength
        contraction_strength = (1 - current_range / (range_ago + 1e-10)) * 100
        
        # Average contraction
        avg_contraction = contraction_strength.rolling(period).mean()
        
        # Squeeze detection (consecutive contractions)
        squeeze_count = range_contracted.rolling(period).sum()
        squeeze_active = (squeeze_count >= period * 0.7).astype(int)
        
        return pd.DataFrame({
            'rci': rci,
            'contraction_strength': contraction_strength,
            'avg_contraction': avg_contraction,
            'squeeze_count': squeeze_count,
            'squeeze_active': squeeze_active,
            'contracting': range_contracted
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        rci_data = self.calculate(data, params)
        threshold = params.get('threshold', 30)
        # Entry when RCI high (contraction) - breakout setup
        # Lockerere Entry-Bedingung: RCI > 60
        entries = (rci_data['rci'] > 60) & (rci_data['rci'].shift(1) <= 60)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (rci_data['rci'] / 100).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        rci_data = self.calculate(data, params)
        threshold = params.get('threshold', 30)
        # Lockerere Entry-Bedingung: RCI > 60
        entries = (rci_data['rci'] > 60) & (rci_data['rci'].shift(1) <= 60)
        exits = (rci_data['rci'] < threshold) & (rci_data['rci'].shift(1) >= threshold)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('range_expansion', index=data.index),
                'signal_strength': (rci_data['rci'] / 100).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        rci_data = self.calculate(data, params)
        return pd.DataFrame({
            'rci': rci_data['rci'],
            'contraction_strength': rci_data['contraction_strength'],
            'squeeze_count': rci_data['squeeze_count'],
            'squeeze_active': rci_data['squeeze_active'],
            'contracting': rci_data['contracting'],
            'rci_slope': rci_data['rci'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
