"""107 - Cyber Cycle"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CyberCycle:
    """Cyber Cycle - Ehlers' cycle indicator"""
    PARAMETERS = {
        'alpha': {'default': 0.07, 'values': [0.03,0.05,0.07,0.1,0.15], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CyberCycle", "Cycle", __version__
    
    def calculate(self, data, params):
        alpha = params.get('alpha', 0.07)
        
        # Smooth price
        smooth = pd.Series(index=data.index, dtype=float)
        smooth.iloc[0] = data['close'].iloc[0]
        smooth.iloc[1] = data['close'].iloc[1]
        
        for i in range(2, len(data)):
            smooth.iloc[i] = (data['close'].iloc[i] + 2 * data['close'].iloc[i-1] + 
                            2 * data['close'].iloc[i-2] + data['close'].iloc[i-3]) / 6 if i >= 3 else data['close'].iloc[i]
        
        # Cyber Cycle
        cycle = pd.Series(0.0, index=data.index)
        
        for i in range(2, len(data)):
            cycle.iloc[i] = ((1 - 0.5 * alpha) ** 2) * (smooth.iloc[i] - 2 * smooth.iloc[i-1] + smooth.iloc[i-2]) + \
                          2 * (1 - alpha) * cycle.iloc[i-1] - ((1 - alpha) ** 2) * cycle.iloc[i-2]
        
        return cycle.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        cycle = self.calculate(data, params)
        # Entry when cycle crosses above 0
        entries = (cycle > 0) & (cycle.shift(1) <= 0)
        
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
                'signal_strength': abs(cycle).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        cycle = self.calculate(data, params)
        entries = (cycle > 0) & (cycle.shift(1) <= 0)
        exits = (cycle < 0) & (cycle.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cycle_cross', index=data.index),
                'signal_strength': abs(cycle).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        cycle = self.calculate(data, params)
        return pd.DataFrame({'cycle_value': cycle, 'cycle_slope': cycle.diff(),
                           'cycle_positive': (cycle > 0).astype(int),
                           'cycle_peak': (cycle > cycle.shift(1)) & (cycle > cycle.shift(-1)),
                           'cycle_trough': (cycle < cycle.shift(1)) & (cycle < cycle.shift(-1))}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
