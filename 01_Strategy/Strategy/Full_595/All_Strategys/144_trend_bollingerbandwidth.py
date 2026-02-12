"""144 - Bollinger Bandwidth"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BollingerBandwidth:
    """Bollinger Bandwidth - Measures band width"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30], 'optimize': True},
        'std_mult': {'default': 2.0, 'values': [1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BollingerBandwidth", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        std_mult = params.get('std_mult', 2.0)
        
        # Bollinger Bands
        ma = data['close'].rolling(period).mean()
        std = data['close'].rolling(period).std()
        upper = ma + (std * std_mult)
        lower = ma - (std * std_mult)
        
        # Bandwidth (percentage)
        bandwidth = ((upper - lower) / ma * 100).fillna(0)
        
        # Bandwidth percentile
        bandwidth_pct = bandwidth.rolling(100).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-10) * 100 if len(x) > 0 else 50
        ).fillna(50)
        
        return pd.DataFrame({
            'bandwidth': bandwidth,
            'bandwidth_pct': bandwidth_pct,
            'upper': upper.fillna(data['close']),
            'middle': ma.fillna(data['close']),
            'lower': lower.fillna(data['close'])
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        bb = self.calculate(data, params)
        # Entry when bandwidth is low (squeeze) and price crosses above MA
        entries = (bb['bandwidth_pct'] < 20) & (data['close'] > bb['middle']) & \
                 (data['close'].shift(1) <= bb['middle'].shift(1))
        
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
                'signal_strength': (100 - bb['bandwidth_pct']) / 100}
    
    def generate_signals_dynamic(self, data, params):
        bb = self.calculate(data, params)
        entries = (bb['bandwidth_pct'] < 20) & (data['close'] > bb['middle']) & \
                 (data['close'].shift(1) <= bb['middle'].shift(1))
        exits = (data['close'] < bb['middle']) & (data['close'].shift(1) >= bb['middle'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bb_cross', index=data.index),
                'signal_strength': (100 - bb['bandwidth_pct']) / 100}
    
    def get_ml_features(self, data, params):
        bb = self.calculate(data, params)
        return pd.DataFrame({
            'bb_bandwidth': bb['bandwidth'],
            'bb_bandwidth_pct': bb['bandwidth_pct'],
            'bb_squeeze': (bb['bandwidth_pct'] < 20).astype(int),
            'bb_expansion': (bb['bandwidth_pct'] > 80).astype(int),
            'bb_position': (data['close'] - bb['lower']) / (bb['upper'] - bb['lower'] + 1e-10)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
