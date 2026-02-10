"""149 - Adaptive ATR"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_AdaptiveATR:
    """Adaptive ATR - Self-Adjusting Volatility Measure"""
    PARAMETERS = {'atr_period': {'default': 14, 'values': [7,11,13,14,17,19,21,23], 'optimize': True}, 'fast_period': {'default': 5, 'values': [3,5,7,8,11], 'optimize': True}, 'slow_period': {'default': 34, 'values': [21,29,34,41,55], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category = "AdaptiveATR", "Volatility"
    def calculate(self, data, params):
        atr_period = params.get('atr_period', 14)
        fast_period = params.get('fast_period', 5)
        slow_period = params.get('slow_period', 34)
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()
        fast_atr = tr.rolling(fast_period).mean()
        slow_atr = tr.rolling(slow_period).mean()
        efficiency_ratio = abs(close - close.shift(atr_period)) / tr.rolling(atr_period).sum()
        adaptive_atr = atr * (1 + efficiency_ratio)
        atr_ratio = fast_atr / slow_atr
        return pd.DataFrame({'atr': atr, 'adaptive_atr': adaptive_atr, 'atr_ratio': atr_ratio, 'efficiency': efficiency_ratio})
    def generate_signals_fixed(self, data, params):
        atr_data = self.calculate(data, params)
        entries = (atr_data['atr_ratio'] > 1.2) & (atr_data['atr_ratio'].shift(1) <= 1.2)
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price, tp_level, sl_level = 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        signal_strength = (atr_data['atr_ratio'] - 1.0).clip(0, 1)
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': signal_strength}
    def generate_signals_dynamic(self, data, params):
        atr_data = self.calculate(data, params)
        entries = (atr_data['atr_ratio'] > 1.2) & (atr_data['atr_ratio'].shift(1) <= 1.2)
        exits = (atr_data['atr_ratio'] < 0.8) & (atr_data['atr_ratio'].shift(1) >= 0.8)
        signal_strength = (atr_data['atr_ratio'] - 1.0).clip(0, 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('adaptive_atr_reverse', index=data.index), 'signal_strength': signal_strength}
    def get_ml_features(self, data, params):
        atr_data = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['adaptive_atr'] = atr_data['adaptive_atr'] / data['close']
        features['atr_ratio'] = atr_data['atr_ratio']
        features['efficiency_ratio'] = atr_data['efficiency']
        features['atr_slope'] = atr_data['atr'].diff()
        features['atr_acceleration'] = atr_data['atr'].diff().diff()
        return features
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
