"""180 - Adaptive Range"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AdaptiveRange:
    """Adaptive Range - Self-Adjusting Range Based on Volatility"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [13,17,19,20,21,23,25,29], 'optimize': True},
        'fast_period': {'default': 5, 'values': [3,5,7,8,11], 'optimize': True},
        'slow_period': {'default': 50, 'values': [34,41,50,55,89], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AdaptiveRange", "Range", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        fast_period = params.get('fast_period', 5)
        slow_period = params.get('slow_period', 50)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Fast and slow ranges
        fast_range = (high.rolling(fast_period).max() - low.rolling(fast_period).min())
        slow_range = (high.rolling(slow_period).max() - low.rolling(slow_period).min())
        
        # Adaptive range (weighted by volatility)
        volatility = close.pct_change().rolling(period).std()
        vol_percentile = volatility.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Adaptive weight (more weight to fast in high vol, slow in low vol)
        adaptive_weight = vol_percentile
        adaptive_range = adaptive_weight * fast_range + (1 - adaptive_weight) * slow_range
        
        # Adaptive boundaries
        adaptive_high = close + adaptive_range / 2
        adaptive_low = close - adaptive_range / 2
        
        # Range efficiency
        range_efficiency = abs(close - close.shift(period)) / (adaptive_range.rolling(period).sum() + 1e-10)
        
        # Adaptive regime
        expanding_regime = (fast_range > slow_range).astype(int)
        
        return pd.DataFrame({
            'adaptive_range': adaptive_range,
            'adaptive_high': adaptive_high,
            'adaptive_low': adaptive_low,
            'adaptive_weight': adaptive_weight,
            'range_efficiency': range_efficiency,
            'expanding_regime': expanding_regime,
            'vol_percentile': vol_percentile
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        adaptive_data = self.calculate(data, params)
        # Entry when price breaks adaptive high
        # Einfachere Entry-Bedingung: Nur MA Crossover
        ma = data['close'].rolling(20).mean()
        entries = (data['close'] > ma) & (data['close'].shift(1) <= ma.shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': adaptive_data['range_efficiency']}
    
    def generate_signals_dynamic(self, data, params):
        adaptive_data = self.calculate(data, params)
        # Gleiche Entry-Bedingung wie Fixed: Nur MA Crossover
        ma = data['close'].rolling(20).mean()
        entries = (data['close'] > ma) & (data['close'].shift(1) <= ma.shift(1))
        exits = (data['close'] < ma) & (data['close'].shift(1) >= ma.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('adaptive_range_exit', index=data.index),
                'signal_strength': adaptive_data['range_efficiency']}
    
    def get_ml_features(self, data, params):
        adaptive_data = self.calculate(data, params)
        return pd.DataFrame({
            'adaptive_range': adaptive_data['adaptive_range'],
            'adaptive_weight': adaptive_data['adaptive_weight'],
            'range_efficiency': adaptive_data['range_efficiency'],
            'expanding_regime': adaptive_data['expanding_regime'],
            'vol_percentile': adaptive_data['vol_percentile'],
            'range_position': (data['close'] - adaptive_data['adaptive_low']) / (adaptive_data['adaptive_range'] + 1e-10)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
