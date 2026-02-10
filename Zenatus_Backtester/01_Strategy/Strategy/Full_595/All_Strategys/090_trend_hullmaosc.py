"""090 - Hull Moving Average Oscillator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HullMAOsc:
    """Hull MA Oscillator - Price minus Hull MA"""
    PARAMETERS = {
        'period': {'default': 16, 'values': [8,11,13,14,16,19,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HullMAOsc", "Momentum", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 16)
        
        # WMA calculation
        def wma(series, length):
            weights = np.arange(1, length + 1)
            return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
        
        # Hull MA
        half_length = int(period / 2)
        sqrt_length = int(np.sqrt(period))
        
        wma_half = wma(data['close'], half_length)
        wma_full = wma(data['close'], period)
        
        raw_hma = 2 * wma_half - wma_full
        hma = wma(raw_hma, sqrt_length)
        
        # Oscillator = Price - HMA
        osc = (data['close'] - hma).fillna(0)
        
        return osc
    
    def generate_signals_fixed(self, data, params):
        osc = self.calculate(data, params)
        # Entry when oscillator crosses above 0
        entries = (osc > 0) & (osc.shift(1) <= 0)
        
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
                'signal_strength': abs(osc).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        osc = self.calculate(data, params)
        entries = (osc > 0) & (osc.shift(1) <= 0)
        exits = (osc < 0) & (osc.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('hullmaosc_cross', index=data.index),
                'signal_strength': abs(osc).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        osc = self.calculate(data, params)
        return pd.DataFrame({'hullmaosc_value': osc, 'hullmaosc_slope': osc.diff(),
                           'hullmaosc_positive': (osc > 0).astype(int),
                           'hullmaosc_increasing': (osc > osc.shift(1)).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
