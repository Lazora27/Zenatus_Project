"""127 - R-Squared"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RSquared:
    """R-Squared - Coefficient of determination for trend strength"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RSquared", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate R-Squared
        rsquared = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            y = data['close'].iloc[i-period:i].values
            x = np.arange(len(y))
            
            if len(y) < period:
                continue
            
            # Linear regression
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            
            # Calculate slope and intercept
            numerator = np.sum((x - x_mean) * (y - y_mean))
            denominator = np.sum((x - x_mean) ** 2)
            
            if denominator > 0:
                slope = numerator / denominator
                intercept = y_mean - slope * x_mean
                
                # Predicted values
                y_pred = slope * x + intercept
                
                # R-squared
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - y_mean) ** 2)
                
                if ss_tot > 0:
                    rsquared.iloc[i] = 1 - (ss_res / ss_tot)
        
        return rsquared.clip(0, 1).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        rsquared = self.calculate(data, params)
        # Entry when R² is high (strong trend)
        entries = (rsquared > 0.7) & (rsquared.shift(1) <= 0.7)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': rsquared}
    
    def generate_signals_dynamic(self, data, params):
        rsquared = self.calculate(data, params)
        entries = (rsquared > 0.7) & (rsquared.shift(1) <= 0.7)
        exits = (rsquared < 0.4) & (rsquared.shift(1) >= 0.4)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('rsq_low', index=data.index),
                'signal_strength': rsquared}
    
    def get_ml_features(self, data, params):
        rsquared = self.calculate(data, params)
        return pd.DataFrame({'rsquared': rsquared, 'rsq_slope': rsquared.diff(),
                           'rsq_high': (rsquared > 0.7).astype(int),
                           'rsq_low': (rsquared < 0.4).astype(int),
                           'rsq_ma': rsquared.rolling(5).mean()}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
