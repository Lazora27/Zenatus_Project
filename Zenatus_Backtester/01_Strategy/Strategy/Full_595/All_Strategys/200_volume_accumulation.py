"""200 - Volume Accumulation"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeAccumulation:
    """Volume Accumulation - Cumulative Volume Analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [13,17,19,20,21,23,25,29], 'optimize': True},
        'threshold': {'default': 0, 'values': [-1000,0,1000,5000,10000], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeAccumulation", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        close, volume = data['close'], data['volume']
        
        # Price direction
        price_up = (close > close.shift(1)).astype(int)
        price_down = (close < close.shift(1)).astype(int)
        
        # Accumulation/Distribution volume
        acc_volume = pd.Series(0.0, index=data.index)
        acc_volume[price_up == 1] = volume[price_up == 1]
        acc_volume[price_down == 1] = -volume[price_down == 1]
        
        # Cumulative Volume Accumulation
        cum_acc = acc_volume.cumsum()
        
        # Rolling accumulation
        rolling_acc = acc_volume.rolling(period).sum()
        
        # Accumulation rate
        acc_rate = rolling_acc / period
        
        # Accumulation momentum
        acc_momentum = rolling_acc.diff()
        
        # Accumulation strength
        total_volume = volume.rolling(period).sum()
        acc_strength = abs(rolling_acc) / (total_volume + 1e-10)
        
        # Accumulation regime
        accumulating = (rolling_acc > 0).astype(int)
        distributing = (rolling_acc < 0).astype(int)
        
        return pd.DataFrame({
            'cum_acc': cum_acc,
            'rolling_acc': rolling_acc,
            'acc_rate': acc_rate,
            'acc_momentum': acc_momentum,
            'acc_strength': acc_strength,
            'accumulating': accumulating,
            'distributing': distributing
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        acc_data = self.calculate(data, params)
        threshold = params.get('threshold', 0)
        
        # Entry when accumulation crosses above threshold
        entries = (acc_data['rolling_acc'] > threshold) & (acc_data['rolling_acc'].shift(1) <= threshold)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': acc_data['acc_strength']}
    
    def generate_signals_dynamic(self, data, params):
        acc_data = self.calculate(data, params)
        threshold = params.get('threshold', 0)
        
        entries = (acc_data['rolling_acc'] > threshold) & (acc_data['rolling_acc'].shift(1) <= threshold)
        exits = (acc_data['rolling_acc'] < -threshold) & (acc_data['rolling_acc'].shift(1) >= -threshold)
        
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('distribution', index=data.index),
                'signal_strength': acc_data['acc_strength']}
    
    def get_ml_features(self, data, params):
        acc_data = self.calculate(data, params)
        return pd.DataFrame({
            'rolling_acc': acc_data['rolling_acc'],
            'acc_rate': acc_data['acc_rate'],
            'acc_momentum': acc_data['acc_momentum'],
            'acc_strength': acc_data['acc_strength'],
            'accumulating': acc_data['accumulating'],
            'distributing': acc_data['distributing'],
            'acc_slope': acc_data['rolling_acc'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
