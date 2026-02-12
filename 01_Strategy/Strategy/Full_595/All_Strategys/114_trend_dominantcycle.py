"""114 - Dominant Cycle Period"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DominantCycle:
    """Dominant Cycle Period - Autocorrelation-based"""
    PARAMETERS = {
        'min_period': {'default': 8, 'values': [6,8,10], 'optimize': True},
        'max_period': {'default': 50, 'values': [40,50,60], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DominantCycle", "Cycle", __version__
    
    def calculate(self, data, params):
        min_period = params.get('min_period', 8)
        max_period = params.get('max_period', 50)
        
        # Detrend price
        detrend = data['close'] - data['close'].rolling(20).mean()
        
        # Find dominant cycle using autocorrelation
        dom_cycle = pd.Series(15.0, index=data.index)  # Default period
        
        for i in range(max_period + 20, len(data)):
            max_corr = 0
            best_period = 15
            
            for period in range(min_period, max_period + 1):
                # Calculate autocorrelation
                if i >= period:
                    current = detrend.iloc[i-period:i].values
                    lagged = detrend.iloc[i-2*period:i-period].values
                    
                    if len(current) == len(lagged) and len(current) > 0:
                        # Pearson correlation
                        if np.std(current) > 0 and np.std(lagged) > 0:
                            corr = np.corrcoef(current, lagged)[0, 1]
                            if not np.isnan(corr) and abs(corr) > max_corr:
                                max_corr = abs(corr)
                                best_period = period
            
            dom_cycle.iloc[i] = best_period
        
        # Smooth the dominant cycle
        dom_cycle_smooth = dom_cycle.rolling(5).median()
        
        return dom_cycle_smooth.fillna(15)
    
    def generate_signals_fixed(self, data, params):
        dom_cycle = self.calculate(data, params)
        # Entry when cycle period is stable (low change)
        cycle_change = abs(dom_cycle.diff())
        entries = (cycle_change < 2) & (cycle_change.shift(1) >= 2)
        
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
                'signal_strength': 1 / (cycle_change + 1)}
    
    def generate_signals_dynamic(self, data, params):
        dom_cycle = self.calculate(data, params)
        cycle_change = abs(dom_cycle.diff())
        entries = (cycle_change < 2) & (cycle_change.shift(1) >= 2)
        exits = (cycle_change > 5) & (cycle_change.shift(1) <= 5)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cycle_unstable', index=data.index),
                'signal_strength': 1 / (cycle_change + 1)}
    
    def get_ml_features(self, data, params):
        dom_cycle = self.calculate(data, params)
        return pd.DataFrame({'dom_cycle': dom_cycle, 'cycle_change': dom_cycle.diff(),
                           'cycle_short': (dom_cycle < 15).astype(int),
                           'cycle_long': (dom_cycle > 30).astype(int),
                           'cycle_stable': (abs(dom_cycle.diff()) < 2).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
