"""125 - Vertical Horizontal Filter (VHF)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VHF:
    """Vertical Horizontal Filter - Trend vs Congestion indicator"""
    PARAMETERS = {
        'period': {'default': 28, 'values': [14,20,28,35,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VHF", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 28)
        
        # Highest high and lowest low
        hh = data['close'].rolling(period).max()
        ll = data['close'].rolling(period).min()
        
        # Numerator: absolute difference between HH and LL
        numerator = abs(hh - ll)
        
        # Denominator: sum of absolute price changes
        price_changes = abs(data['close'].diff())
        denominator = price_changes.rolling(period).sum()
        
        # VHF
        vhf = (numerator / (denominator + 1e-10)).fillna(0)
        
        return vhf
    
    def generate_signals_fixed(self, data, params):
        vhf = self.calculate(data, params)
        # Entry when VHF is high (trending market)
        entries = (vhf > 0.4) & (vhf.shift(1) <= 0.4)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vhf.clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        vhf = self.calculate(data, params)
        entries = (vhf > 0.4) & (vhf.shift(1) <= 0.4)
        exits = (vhf < 0.25) & (vhf.shift(1) >= 0.25)  # Exit when congestion
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('vhf_congestion', index=data.index),
                'signal_strength': vhf.clip(0, 1)}
    
    def get_ml_features(self, data, params):
        vhf = self.calculate(data, params)
        return pd.DataFrame({
            'vhf_value': vhf,
            'vhf_slope': vhf.diff(),
            'vhf_trending': (vhf > 0.4).astype(int),
            'vhf_congestion': (vhf < 0.25).astype(int),
            'vhf_ma': vhf.rolling(10).mean()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
