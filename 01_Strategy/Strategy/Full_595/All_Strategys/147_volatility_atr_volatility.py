"""147 - ATR Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_ATRVolatility:
    """ATR Volatility - Normalized Volatility Measure"""
    PARAMETERS = {'atr_period': {'default': 14, 'values': [7,11,13,14,17,19,21,23], 'optimize': True}, 'smooth_period': {'default': 5, 'values': [3,5,7,8,11,13], 'optimize': True}, 'threshold': {'default': 1.5, 'values': [1.0,1.2,1.5,1.8,2.0,2.5], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category = "ATRVolatility", "Volatility"
    def calculate(self, data, params):
        atr_period = params.get('atr_period', 14)
        smooth_period = params.get('smooth_period', 5)
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()
        atr_normalized = (atr / close) * 100
        atr_smooth = atr_normalized.rolling(smooth_period).mean()
        atr_std = atr_normalized.rolling(atr_period).std()
        volatility_ratio = (atr_normalized - atr_smooth) / atr_std
        return pd.DataFrame({'atr': atr, 'atr_normalized': atr_normalized, 'volatility_ratio': volatility_ratio})
    def generate_signals_fixed(self, data, params):
        vol = self.calculate(data, params)
        threshold = params.get('threshold', 1.5)
        entries = (vol['volatility_ratio'] > threshold) & (vol['volatility_ratio'].shift(1) <= threshold)
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
        signal_strength = abs(vol['volatility_ratio']) / 3.0
        signal_strength = signal_strength.clip(0, 1)
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': signal_strength}
    def generate_signals_dynamic(self, data, params):
        vol = self.calculate(data, params)
        threshold = params.get('threshold', 1.5)
        entries = (vol['volatility_ratio'] > threshold) & (vol['volatility_ratio'].shift(1) <= threshold)
        exits = (vol['volatility_ratio'] < -threshold) & (vol['volatility_ratio'].shift(1) >= -threshold)
        signal_strength = abs(vol['volatility_ratio']) / 3.0
        signal_strength = signal_strength.clip(0, 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('volatility_normalized', index=data.index), 'signal_strength': signal_strength}
    def get_ml_features(self, data, params):
        vol = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['atr_normalized'] = vol['atr_normalized']
        features['volatility_ratio'] = vol['volatility_ratio']
        features['atr_percentile'] = vol['atr_normalized'].rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        features['volatility_slope'] = vol['volatility_ratio'].diff()
        return features
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
