"""104 - Relative Momentum Index (RMI)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RMI:
    """Relative Momentum Index - RSI with momentum period"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21], 'optimize': True},
        'momentum_period': {'default': 5, 'values': [3,5,7,8,10], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RMI", "Momentum", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        momentum_period = params.get('momentum_period', 5)
        
        # Calculate momentum (price change over momentum_period)
        momentum = data['close'].diff(momentum_period)
        
        # Separate gains and losses
        gain = momentum.where(momentum > 0, 0)
        loss = -momentum.where(momentum < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        
        # Calculate RS and RMI
        rs = avg_gain / (avg_loss + 1e-10)
        rmi = 100 - (100 / (1 + rs))
        
        return rmi.fillna(50)
    
    def generate_signals_fixed(self, data, params):
        rmi = self.calculate(data, params)
        # Entry when crosses above 30 (oversold)
        entries = (rmi > 30) & (rmi.shift(1) <= 30)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(rmi - 50) / 50}
    
    def generate_signals_dynamic(self, data, params):
        rmi = self.calculate(data, params)
        entries = (rmi > 30) & (rmi.shift(1) <= 30)
        exits = (rmi > 70) & (rmi.shift(1) <= 70)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('rmi_overbought', index=data.index),
                'signal_strength': abs(rmi - 50) / 50}
    
    def get_ml_features(self, data, params):
        rmi = self.calculate(data, params)
        return pd.DataFrame({'rmi_value': rmi, 'rmi_slope': rmi.diff(),
                           'rmi_overbought': (rmi > 70).astype(int),
                           'rmi_oversold': (rmi < 30).astype(int),
                           'rmi_divergence': rmi - rmi.rolling(14).mean()}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
