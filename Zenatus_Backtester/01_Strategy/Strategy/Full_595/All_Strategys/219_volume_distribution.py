"""219 - Volume Distribution"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeDistribution:
    """Volume Distribution - Volume Allocation Analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeDistribution", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        close, volume = data['close'], data['volume']
        
        # Volume Distribution by Price Level
        price_up = (close > close.shift(1)).astype(int)
        price_down = (close < close.shift(1)).astype(int)
        
        # Up/Down Volume
        up_volume = volume * price_up
        down_volume = volume * price_down
        
        # Distribution Ratio
        total_up = up_volume.rolling(period).sum()
        total_down = down_volume.rolling(period).sum()
        distribution_ratio = total_up / (total_down + 1e-10)
        
        # Volume Concentration (Gini-like)
        vol_std = volume.rolling(period).std()
        vol_mean = volume.rolling(period).mean()
        concentration = vol_std / (vol_mean + 1e-10)
        
        # Balanced/Imbalanced Distribution
        balanced = (distribution_ratio > 0.8) & (distribution_ratio < 1.2)
        imbalanced_bullish = (distribution_ratio > 1.5).astype(int)
        imbalanced_bearish = (distribution_ratio < 0.67).astype(int)
        
        return pd.DataFrame({
            'up_volume': total_up,
            'down_volume': total_down,
            'distribution_ratio': distribution_ratio,
            'concentration': concentration,
            'balanced': balanced.astype(int),
            'imbalanced_bullish': imbalanced_bullish,
            'imbalanced_bearish': imbalanced_bearish
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vd_data = self.calculate(data, params)
        entries = (vd_data['imbalanced_bullish'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vd_data['distribution_ratio'].clip(0, 3)/3}
    
    def generate_signals_dynamic(self, data, params):
        vd_data = self.calculate(data, params)
        entries = (vd_data['imbalanced_bullish'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (vd_data['balanced'] == 1) | (vd_data['imbalanced_bearish'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('distribution_change', index=data.index),
                'signal_strength': vd_data['distribution_ratio'].clip(0, 3)/3}
    
    def get_ml_features(self, data, params):
        vd_data = self.calculate(data, params)
        return pd.DataFrame({
            'up_volume': vd_data['up_volume'],
            'down_volume': vd_data['down_volume'],
            'distribution_ratio': vd_data['distribution_ratio'],
            'concentration': vd_data['concentration'],
            'imbalanced_bullish': vd_data['imbalanced_bullish'],
            'imbalanced_bearish': vd_data['imbalanced_bearish']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
