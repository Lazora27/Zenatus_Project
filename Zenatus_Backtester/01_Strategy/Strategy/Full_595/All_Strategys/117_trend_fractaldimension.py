"""117 - Fractal Dimension"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FractalDimension:
    """Fractal Dimension - Market complexity measure"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FractalDimension", "Complexity", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate Fractal Dimension using Higuchi method
        fd = pd.Series(1.5, index=data.index)  # Default value
        
        for i in range(period, len(data)):
            prices = data['close'].iloc[i-period:i].values
            
            if len(prices) < period:
                continue
            
            # Higuchi Fractal Dimension
            k_max = min(8, period // 2)
            lk = []
            
            for k in range(1, k_max + 1):
                lm = []
                for m in range(k):
                    ll = 0
                    n_max = int((period - m - 1) / k)
                    
                    for j in range(1, n_max + 1):
                        if m + j * k < len(prices):
                            ll += abs(prices[m + j * k] - prices[m + (j - 1) * k])
                    
                    if n_max > 0:
                        ll = ll * (period - 1) / (n_max * k * k)
                        lm.append(ll)
                
                if lm:
                    lk.append(np.mean(lm))
            
            # Calculate slope (Fractal Dimension)
            if len(lk) > 1:
                x = np.log([k for k in range(1, len(lk) + 1)])
                y = np.log(lk)
                
                if len(x) > 1 and np.std(x) > 0:
                    slope = np.polyfit(x, y, 1)[0]
                    fd.iloc[i] = -slope  # Negative slope is FD
        
        return fd.clip(1.0, 2.0).fillna(1.5)
    
    def generate_signals_fixed(self, data, params):
        fd = self.calculate(data, params)
        # Entry when FD is low (trending market)
        entries = (fd < 1.3) & (fd.shift(1) >= 1.3)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': 2 - fd}
    
    def generate_signals_dynamic(self, data, params):
        fd = self.calculate(data, params)
        entries = (fd < 1.3) & (fd.shift(1) >= 1.3)
        exits = (fd > 1.7) & (fd.shift(1) <= 1.7)  # Exit when choppy
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('fd_choppy', index=data.index),
                'signal_strength': 2 - fd}
    
    def get_ml_features(self, data, params):
        fd = self.calculate(data, params)
        return pd.DataFrame({'fd_value': fd, 'fd_slope': fd.diff(),
                           'fd_trending': (fd < 1.3).astype(int),
                           'fd_ranging': (fd > 1.7).astype(int),
                           'fd_normalized': (fd - 1) / 1}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
