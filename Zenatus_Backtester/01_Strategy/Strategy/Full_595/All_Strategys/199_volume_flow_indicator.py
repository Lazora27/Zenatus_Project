"""199 - Volume Flow Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeFlowIndicator:
    """Volume Flow Indicator - Directional Volume Flow Analysis"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21,23], 'optimize': True},
        'threshold': {'default': 0, 'values': [-20,-10,0,10,20], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeFlowIndicator", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Typical Price
        typical_price = (high + low + close) / 3
        
        # Money Flow Multiplier
        mf_multiplier = ((close - low) - (high - close)) / (high - low + 1e-10)
        
        # Money Flow Volume
        mf_volume = mf_multiplier * volume
        
        # Positive and Negative Flow
        positive_flow = pd.Series(0.0, index=data.index)
        negative_flow = pd.Series(0.0, index=data.index)
        
        positive_flow[mf_volume > 0] = mf_volume[mf_volume > 0]
        negative_flow[mf_volume < 0] = abs(mf_volume[mf_volume < 0])
        
        # Volume Flow Indicator
        pos_sum = positive_flow.rolling(period).sum()
        neg_sum = negative_flow.rolling(period).sum()
        vfi = ((pos_sum - neg_sum) / (pos_sum + neg_sum + 1e-10)) * 100
        
        # Smoothed VFI
        vfi_smooth = vfi.ewm(span=3).mean()
        
        # VFI divergence from zero
        vfi_strength = abs(vfi)
        
        # Flow direction
        flow_bullish = (vfi > 0).astype(int)
        flow_bearish = (vfi < 0).astype(int)
        
        return pd.DataFrame({
            'vfi': vfi,
            'vfi_smooth': vfi_smooth,
            'vfi_strength': vfi_strength,
            'positive_flow': pos_sum,
            'negative_flow': neg_sum,
            'flow_bullish': flow_bullish,
            'flow_bearish': flow_bearish
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vfi_data = self.calculate(data, params)
        threshold = params.get('threshold', 0)
        
        # Entry when VFI crosses above threshold
        entries = (vfi_data['vfi'] > threshold) & (vfi_data['vfi'].shift(1) <= threshold)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (vfi_data['vfi'] / 100).clip(-1, 1)}
    
    def generate_signals_dynamic(self, data, params):
        vfi_data = self.calculate(data, params)
        threshold = params.get('threshold', 0)
        
        entries = (vfi_data['vfi'] > threshold) & (vfi_data['vfi'].shift(1) <= threshold)
        exits = (vfi_data['vfi'] < -threshold) & (vfi_data['vfi'].shift(1) >= -threshold)
        
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('negative_flow', index=data.index),
                'signal_strength': (vfi_data['vfi'] / 100).clip(-1, 1)}
    
    def get_ml_features(self, data, params):
        vfi_data = self.calculate(data, params)
        return pd.DataFrame({
            'vfi': vfi_data['vfi'],
            'vfi_smooth': vfi_data['vfi_smooth'],
            'vfi_strength': vfi_data['vfi_strength'],
            'flow_bullish': vfi_data['flow_bullish'],
            'flow_bearish': vfi_data['flow_bearish'],
            'vfi_slope': vfi_data['vfi'].diff(),
            'flow_ratio': vfi_data['positive_flow'] / (vfi_data['negative_flow'] + 1e-10)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
