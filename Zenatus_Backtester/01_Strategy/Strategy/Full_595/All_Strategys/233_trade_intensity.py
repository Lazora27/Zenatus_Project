"""233 - Trade Intensity"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TradeIntensity:
    """Trade Intensity - Trading Activity Concentration"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TradeIntensity", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        close, volume = data['close'], data['volume']
        
        # Trade Intensity (volume per price change)
        price_change = abs(close.diff())
        intensity = volume / (price_change + 1e-10)
        
        # Intensity MA
        intensity_ma = intensity.rolling(period).mean()
        
        # Relative Intensity
        relative_intensity = intensity / (intensity_ma + 1e-10)
        
        # High/Low Intensity
        high_intensity = (relative_intensity > 1.5).astype(int)
        low_intensity = (relative_intensity < 0.7).astype(int)
        
        # Intensity Trend
        intensity_trend = (intensity > intensity.shift(1)).astype(int)
        
        # Intensity Momentum
        intensity_momentum = intensity.diff(period)
        
        # Normalized Intensity
        intensity_normalized = (intensity - intensity.rolling(100).min()) / (
            intensity.rolling(100).max() - intensity.rolling(100).min() + 1e-10
        )
        
        return pd.DataFrame({
            'intensity': intensity,
            'intensity_ma': intensity_ma,
            'relative_intensity': relative_intensity,
            'high_intensity': high_intensity,
            'low_intensity': low_intensity,
            'intensity_trend': intensity_trend,
            'intensity_normalized': intensity_normalized
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ti_data = self.calculate(data, params)
        entries = (ti_data['high_intensity'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': ti_data['intensity_normalized']}
    
    def generate_signals_dynamic(self, data, params):
        ti_data = self.calculate(data, params)
        entries = (ti_data['high_intensity'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (ti_data['low_intensity'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('low_intensity', index=data.index),
                'signal_strength': ti_data['intensity_normalized']}
    
    def get_ml_features(self, data, params):
        ti_data = self.calculate(data, params)
        return pd.DataFrame({
            'relative_intensity': ti_data['relative_intensity'],
            'high_intensity': ti_data['high_intensity'],
            'low_intensity': ti_data['low_intensity'],
            'intensity_trend': ti_data['intensity_trend'],
            'intensity_normalized': ti_data['intensity_normalized']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
