"""189 - Volume Rate of Change"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeRateOfChange:
    """Volume Rate of Change - Measures Volume Momentum"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23], 'optimize': True},
        'threshold': {'default': 50, 'values': [30,40,50,60,75,100], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeRateOfChange", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        volume = data['volume']
        
        # Volume Rate of Change (VROC)
        vroc = ((volume - volume.shift(period)) / (volume.shift(period) + 1e-10)) * 100
        
        # Smoothed VROC
        vroc_smooth = vroc.ewm(span=5).mean()
        
        # VROC percentile rank
        vroc_rank = vroc.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Volume acceleration
        vol_acceleration = vroc.diff()
        
        # Volume expansion/contraction
        vol_expanding = (vroc > 0).astype(int)
        vol_contracting = (vroc < 0).astype(int)
        
        # Extreme volume detection
        extreme_high = (vroc > vroc.rolling(100).quantile(0.9)).astype(int)
        extreme_low = (vroc < vroc.rolling(100).quantile(0.1)).astype(int)
        
        return pd.DataFrame({
            'vroc': vroc,
            'vroc_smooth': vroc_smooth,
            'vroc_rank': vroc_rank,
            'vol_acceleration': vol_acceleration,
            'vol_expanding': vol_expanding,
            'vol_contracting': vol_contracting,
            'extreme_high': extreme_high,
            'extreme_low': extreme_low
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vroc_data = self.calculate(data, params)
        threshold = params.get('threshold', 50)
        
        # Entry when volume expanding significantly
        entries = (vroc_data['vroc'] > threshold) & (vroc_data['vroc'].shift(1) <= threshold) & (data['close'] > data['close'].shift(1))
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vroc_data['vroc_rank']}
    
    def generate_signals_dynamic(self, data, params):
        vroc_data = self.calculate(data, params)
        threshold = params.get('threshold', 50)
        
        entries = (vroc_data['vroc'] > threshold) & (vroc_data['vroc'].shift(1) <= threshold) & (data['close'] > data['close'].shift(1))
        exits = (vroc_data['vroc'] < -threshold) | (vroc_data['vol_contracting'] == 1)
        
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('volume_contraction', index=data.index),
                'signal_strength': vroc_data['vroc_rank']}
    
    def get_ml_features(self, data, params):
        vroc_data = self.calculate(data, params)
        return pd.DataFrame({
            'vroc': vroc_data['vroc'],
            'vroc_smooth': vroc_data['vroc_smooth'],
            'vroc_rank': vroc_data['vroc_rank'],
            'vol_acceleration': vroc_data['vol_acceleration'],
            'vol_expanding': vroc_data['vol_expanding'],
            'extreme_high': vroc_data['extreme_high'],
            'extreme_low': vroc_data['extreme_low']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
