"""075 - SMI Ergodic"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SMIErgodic:
    """SMI Ergodic - Stochastic Momentum Index Ergodic"""
    PARAMETERS = {
        'ema1': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'ema2': {'default': 20, 'values': [13,17,19,20,21,23], 'optimize': True},
        'signal': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SMIErgodic", "Momentum", __version__
    
    def calculate(self, data, params):
        ema1 = params.get('ema1', 5)
        ema2 = params.get('ema2', 20)
        signal_period = params.get('signal', 5)
        
        # Price change
        price_change = data['close'].diff()
        
        # Double smoothed price change
        smi = price_change.ewm(span=ema1).mean().ewm(span=ema2).mean()
        
        # Signal line
        signal = smi.ewm(span=signal_period).mean()
        
        return pd.DataFrame({'smi': smi.fillna(0), 'signal': signal.fillna(0)}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when SMI crosses above signal
        entries = (result['smi'] > result['signal']) & (result['smi'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['smi'] - result['signal']).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['smi'] > result['signal']) & (result['smi'].shift(1) <= result['signal'].shift(1))
        exits = (result['smi'] < result['signal']) & (result['smi'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('smi_cross', index=data.index),
                'signal_strength': abs(result['smi'] - result['signal']).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'smi_value': result['smi'], 'smi_signal': result['signal'],
                           'smi_divergence': result['smi'] - result['signal'],
                           'smi_slope': result['smi'].diff()}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
