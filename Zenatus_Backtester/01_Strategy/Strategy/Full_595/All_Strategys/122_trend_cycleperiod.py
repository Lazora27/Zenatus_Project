"""122 - Cycle Period Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CyclePeriod:
    """Cycle Period - Adaptive cycle length detector"""
    PARAMETERS = {
        'min_period': {'default': 8, 'values': [6,8,10], 'optimize': True},
        'max_period': {'default': 50, 'values': [40,50,60], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CyclePeriod", "Cycle", __version__
    
    def calculate(self, data, params):
        min_period = params.get('min_period', 8)
        max_period = params.get('max_period', 50)
        
        # Smooth price
        smooth = data['close'].rolling(4).mean()
        
        # Calculate cycle using zero crossings
        cycle_period = pd.Series(20.0, index=data.index)
        
        for i in range(max_period + 10, len(data)):
            # Detrend
            detrend = smooth.iloc[i] - smooth.iloc[i-1]
            
            # Find zero crossings in recent data
            recent_data = smooth.iloc[i-max_period:i].diff()
            
            # Count zero crossings
            zero_cross = ((recent_data > 0) & (recent_data.shift(1) <= 0)) | \
                        ((recent_data < 0) & (recent_data.shift(1) >= 0))
            
            crossings = zero_cross.sum()
            
            if crossings > 1:
                # Estimate period from crossings
                period = len(recent_data) / (crossings / 2)
                cycle_period.iloc[i] = np.clip(period, min_period, max_period)
        
        # Smooth the cycle period
        cycle_smooth = cycle_period.rolling(5).median()
        
        return cycle_smooth.fillna(20)
    
    def generate_signals_fixed(self, data, params):
        cycle_period = self.calculate(data, params)
        # Entry when cycle period is short (fast market)
        entries = (cycle_period < 15) & (cycle_period.shift(1) >= 15)
        
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
                'signal_strength': 1 / (cycle_period / 10)}
    
    def generate_signals_dynamic(self, data, params):
        cycle_period = self.calculate(data, params)
        entries = (cycle_period < 15) & (cycle_period.shift(1) >= 15)
        exits = (cycle_period > 30) & (cycle_period.shift(1) <= 30)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cycle_slow', index=data.index),
                'signal_strength': 1 / (cycle_period / 10)}
    
    def get_ml_features(self, data, params):
        cycle_period = self.calculate(data, params)
        return pd.DataFrame({
            'cycle_period': cycle_period,
            'cycle_change': cycle_period.diff(),
            'cycle_fast': (cycle_period < 15).astype(int),
            'cycle_slow': (cycle_period > 30).astype(int),
            'cycle_normalized': cycle_period / 50
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
