"""101 - Inverse Fisher Transform"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_InverseFisher:
    """Inverse Fisher Transform - Normalizes indicators to -1 to +1 range"""
    PARAMETERS = {
        'period': {'default': 9, 'values': [5,7,8,9,11,13,14,17], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "InverseFisher", "Momentum", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 9)
        
        # Calculate RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Normalize RSI to -5 to +5
        v1 = 0.1 * (rsi - 50)
        
        # Weighted Moving Average
        wma = v1.rolling(period).mean()
        
        # Inverse Fisher Transform
        ift = (np.exp(2 * wma) - 1) / (np.exp(2 * wma) + 1)
        
        return ift.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ift = self.calculate(data, params)
        # Entry when crosses above 0
        entries = (ift > 0) & (ift.shift(1) <= 0)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(ift)}
    
    def generate_signals_dynamic(self, data, params):
        ift = self.calculate(data, params)
        entries = (ift > 0) & (ift.shift(1) <= 0)
        exits = (ift < 0) & (ift.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('ift_cross', index=data.index),
                'signal_strength': abs(ift)}
    
    def get_ml_features(self, data, params):
        ift = self.calculate(data, params)
        return pd.DataFrame({'ift_value': ift, 'ift_slope': ift.diff(),
                           'ift_positive': (ift > 0).astype(int),
                           'ift_overbought': (ift > 0.5).astype(int),
                           'ift_oversold': (ift < -0.5).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
