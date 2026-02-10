"""070 - KDJ (Stochastic with J Line)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_KDJ:
    """KDJ - Stochastic with J Line"""
    PARAMETERS = {
        'k_period': {'default': 9, 'values': [5,7,8,9,11,13,14,17,19,21], 'optimize': True},
        'd_period': {'default': 3, 'values': [2,3,5,7,8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "KDJ", "Momentum", __version__
    
    def calculate(self, data, params):
        k_period = params.get('k_period', 9)
        d_period = params.get('d_period', 3)
        
        # Stochastic K
        low_min = data['low'].rolling(k_period).min()
        high_max = data['high'].rolling(k_period).max()
        k = 100 * (data['close'] - low_min) / (high_max - low_min + 1e-10)
        
        # D = SMA of K
        d = k.rolling(d_period).mean()
        
        # J = 3K - 2D
        j = 3 * k - 2 * d
        
        return pd.DataFrame({'k': k.fillna(50), 'd': d.fillna(50), 'j': j.fillna(50)}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry: K crosses above D and J < 20 (oversold)
        entries = (result['k'] > result['d']) & (result['k'].shift(1) <= result['d'].shift(1)) & (result['j'] < 20)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(result['k'] - result['d']) / 100}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['k'] > result['d']) & (result['k'].shift(1) <= result['d'].shift(1)) & (result['j'] < 20)
        exits = (result['k'] < result['d']) & (result['k'].shift(1) >= result['d'].shift(1)) & (result['j'] > 80)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('kdj_cross', index=data.index),
                'signal_strength': abs(result['k'] - result['d']) / 100}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'kdj_k': result['k'], 'kdj_d': result['d'], 'kdj_j': result['j'],
                           'kdj_divergence': result['k'] - result['d']}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
