"""206 - Volume Weighted Moving Average"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeWeightedMA:
    """Volume Weighted Moving Average - Price weighted by Volume"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeWeightedMA", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        close, volume = data['close'], data['volume']
        
        # Volume Weighted MA
        vwma = (close * volume).rolling(period).sum() / volume.rolling(period).sum()
        
        # Distance from VWMA
        distance = (close - vwma) / close
        
        # VWMA Slope
        vwma_slope = vwma.diff()
        
        # Above/Below VWMA
        above_vwma = (close > vwma).astype(int)
        
        return pd.DataFrame({
            'vwma': vwma,
            'distance': distance,
            'vwma_slope': vwma_slope,
            'above_vwma': above_vwma
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vwma_data = self.calculate(data, params)
        entries = (data['close'] > vwma_data['vwma']) & (data['close'].shift(1) <= vwma_data['vwma'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(vwma_data['distance'])}
    
    def generate_signals_dynamic(self, data, params):
        vwma_data = self.calculate(data, params)
        entries = (data['close'] > vwma_data['vwma']) & (data['close'].shift(1) <= vwma_data['vwma'].shift(1))
        exits = (data['close'] < vwma_data['vwma']) & (data['close'].shift(1) >= vwma_data['vwma'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('vwma_cross', index=data.index),
                'signal_strength': abs(vwma_data['distance'])}
    
    def get_ml_features(self, data, params):
        vwma_data = self.calculate(data, params)
        return pd.DataFrame({
            'vwma': vwma_data['vwma'],
            'distance': vwma_data['distance'],
            'vwma_slope': vwma_data['vwma_slope'],
            'above_vwma': vwma_data['above_vwma']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
