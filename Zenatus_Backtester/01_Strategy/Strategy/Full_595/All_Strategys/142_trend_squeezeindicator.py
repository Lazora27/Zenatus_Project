"""142 - Squeeze Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SqueezeIndicator:
    """Squeeze Indicator - Bollinger Bands inside Keltner Channels"""
    PARAMETERS = {
        'bb_period': {'default': 20, 'values': [14,20,25,30], 'optimize': True},
        'bb_mult': {'default': 2.0, 'values': [1.5,2.0,2.5], 'optimize': True},
        'kc_period': {'default': 20, 'values': [14,20,25,30], 'optimize': True},
        'kc_mult': {'default': 1.5, 'values': [1.0,1.5,2.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SqueezeIndicator", "Volatility", __version__
    
    def calculate(self, data, params):
        bb_period = params.get('bb_period', 20)
        bb_mult = params.get('bb_mult', 2.0)
        kc_period = params.get('kc_period', 20)
        kc_mult = params.get('kc_mult', 1.5)
        
        # Bollinger Bands
        bb_ma = data['close'].rolling(bb_period).mean()
        bb_std = data['close'].rolling(bb_period).std()
        bb_upper = bb_ma + (bb_std * bb_mult)
        bb_lower = bb_ma - (bb_std * bb_mult)
        
        # Keltner Channels
        kc_ma = data['close'].rolling(kc_period).mean()
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(kc_period).mean()
        kc_upper = kc_ma + (atr * kc_mult)
        kc_lower = kc_ma - (atr * kc_mult)
        
        # Squeeze: BB inside KC
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        squeeze_off = (bb_lower < kc_lower) | (bb_upper > kc_upper)
        
        # Momentum
        highest = data['high'].rolling(kc_period).max()
        lowest = data['low'].rolling(kc_period).min()
        avg_hl = (highest + lowest) / 2
        momentum = data['close'] - avg_hl
        
        return pd.DataFrame({
            'squeeze_on': squeeze_on.astype(int),
            'squeeze_off': squeeze_off.astype(int),
            'momentum': momentum.fillna(0)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        squeeze = self.calculate(data, params)
        # Entry when squeeze turns off and momentum is positive
        entries = (squeeze['squeeze_off'] == 1) & (squeeze['squeeze_on'].shift(1) == 1) & (squeeze['momentum'] > 0)
        
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
                'signal_strength': abs(squeeze['momentum']).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        squeeze = self.calculate(data, params)
        entries = (squeeze['squeeze_off'] == 1) & (squeeze['squeeze_on'].shift(1) == 1) & (squeeze['momentum'] > 0)
        exits = (squeeze['momentum'] < 0) & (squeeze['momentum'].shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('momentum_neg', index=data.index),
                'signal_strength': abs(squeeze['momentum']).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        squeeze = self.calculate(data, params)
        return pd.DataFrame({
            'squeeze_on': squeeze['squeeze_on'],
            'squeeze_off': squeeze['squeeze_off'],
            'squeeze_momentum': squeeze['momentum'],
            'squeeze_mom_positive': (squeeze['momentum'] > 0).astype(int),
            'squeeze_firing': ((squeeze['squeeze_off'] == 1) & (squeeze['squeeze_on'].shift(1) == 1)).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
