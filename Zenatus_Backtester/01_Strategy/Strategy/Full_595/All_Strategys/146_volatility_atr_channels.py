"""146 - ATR Channels"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_ATRChannels:
    """ATR Channels - Dynamic Price Channels"""
    PARAMETERS = {'atr_period': {'default': 14, 'values': [7,11,13,14,17,19,21,23], 'optimize': True}, 'ma_period': {'default': 20, 'values': [13,17,19,20,21,23,25,29], 'optimize': True}, 'multiplier': {'default': 2.0, 'values': [1.0,1.5,2.0,2.5,3.0], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category = "ATRChannels", "Volatility"
    def calculate(self, data, params):
        atr_period = params.get('atr_period', 14)
        ma_period = params.get('ma_period', 20)
        multiplier = params.get('multiplier', 2.0)
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()
        ma = close.rolling(ma_period).mean()
        upper = ma + (atr * multiplier)
        lower = ma - (atr * multiplier)
        return pd.DataFrame({'ma': ma, 'upper': upper, 'lower': lower, 'atr': atr})
    def generate_signals_fixed(self, data, params):
        channels = self.calculate(data, params)
        entries = (data['close'] > channels['upper']) & (data['close'].shift(1) <= channels['upper'].shift(1))
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
        signal_strength = abs(data['close'] - channels['ma']) / channels['atr']
        signal_strength = signal_strength.clip(0, 1)
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': signal_strength}
    def generate_signals_dynamic(self, data, params):
        channels = self.calculate(data, params)
        entries = (data['close'] > channels['upper']) & (data['close'].shift(1) <= channels['upper'].shift(1))
        exits = (data['close'] < channels['ma']) & (data['close'].shift(1) >= channels['ma'].shift(1))
        signal_strength = abs(data['close'] - channels['ma']) / channels['atr']
        signal_strength = signal_strength.clip(0, 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('atr_channel_cross', index=data.index), 'signal_strength': signal_strength}
    def get_ml_features(self, data, params):
        channels = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['channel_position'] = (data['close'] - channels['lower']) / (channels['upper'] - channels['lower'])
        features['distance_ma'] = (data['close'] - channels['ma']) / channels['atr']
        features['channel_width'] = (channels['upper'] - channels['lower']) / channels['ma']
        features['atr_slope'] = channels['atr'].diff()
        return features
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
