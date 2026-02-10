"""217 - Volume Strength"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeStrength:
    """Volume Strength - Relative Volume Power"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeStrength", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        close, volume = data['close'], data['volume']
        
        # Volume Strength Index
        price_change = close.diff()
        vol_strength = volume * np.sign(price_change)
        
        # Cumulative Strength
        cumulative_strength = vol_strength.rolling(period).sum()
        
        # Relative Strength
        total_volume = volume.rolling(period).sum()
        relative_strength = cumulative_strength / (total_volume + 1e-10)
        
        # Strength Percentile
        strength_percentile = cumulative_strength.rolling(100).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        # Strong/Weak Classification
        strong = (relative_strength > 0.2).astype(int)
        weak = (relative_strength < -0.2).astype(int)
        
        return pd.DataFrame({
            'vol_strength': vol_strength,
            'cumulative_strength': cumulative_strength,
            'relative_strength': relative_strength,
            'strength_percentile': strength_percentile,
            'strong': strong,
            'weak': weak
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vs_data = self.calculate(data, params)
        entries = (vs_data['strong'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vs_data['strength_percentile']}
    
    def generate_signals_dynamic(self, data, params):
        vs_data = self.calculate(data, params)
        entries = (vs_data['strong'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (vs_data['weak'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('weak_strength', index=data.index),
                'signal_strength': vs_data['strength_percentile']}
    
    def get_ml_features(self, data, params):
        vs_data = self.calculate(data, params)
        return pd.DataFrame({
            'cumulative_strength': vs_data['cumulative_strength'],
            'relative_strength': vs_data['relative_strength'],
            'strength_percentile': vs_data['strength_percentile'],
            'strong': vs_data['strong'],
            'weak': vs_data['weak']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
