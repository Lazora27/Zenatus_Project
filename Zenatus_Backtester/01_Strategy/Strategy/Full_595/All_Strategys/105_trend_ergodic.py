"""105 - Ergodic Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Ergodic:
    """Ergodic Indicator - True Strength Index variant"""
    PARAMETERS = {
        'long_period': {'default': 32, 'values': [20,25,32,40,50], 'optimize': True},
        'short_period': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'signal_period': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Ergodic", "Momentum", __version__
    
    def calculate(self, data, params):
        long_period = params.get('long_period', 32)
        short_period = params.get('short_period', 5)
        signal_period = params.get('signal_period', 5)
        
        # Price momentum
        momentum = data['close'].diff()
        
        # Double smoothed momentum
        ema1 = momentum.ewm(span=long_period).mean()
        ema2 = ema1.ewm(span=short_period).mean()
        
        # Double smoothed absolute momentum
        abs_momentum = abs(momentum)
        abs_ema1 = abs_momentum.ewm(span=long_period).mean()
        abs_ema2 = abs_ema1.ewm(span=short_period).mean()
        
        # Ergodic = (Double smoothed momentum / Double smoothed abs momentum) * 100
        ergodic = (ema2 / (abs_ema2 + 1e-10) * 100).fillna(0)
        
        # Signal line
        signal = ergodic.ewm(span=signal_period).mean()
        
        return pd.DataFrame({'ergodic': ergodic, 'signal': signal}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when ergodic crosses above signal
        entries = (result['ergodic'] > result['signal']) & (result['ergodic'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['ergodic'] - result['signal']).clip(0, 10) / 10}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['ergodic'] > result['signal']) & (result['ergodic'].shift(1) <= result['signal'].shift(1))
        exits = (result['ergodic'] < result['signal']) & (result['ergodic'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('ergodic_cross', index=data.index),
                'signal_strength': abs(result['ergodic'] - result['signal']).clip(0, 10) / 10}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'ergodic_value': result['ergodic'], 'ergodic_signal': result['signal'],
                           'ergodic_divergence': result['ergodic'] - result['signal'],
                           'ergodic_slope': result['ergodic'].diff(),
                           'ergodic_positive': (result['ergodic'] > 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
