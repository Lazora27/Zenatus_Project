"""028 - Aroon Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_Aroon:
    """Aroon Indicator - Trend Strength"""
    PARAMETERS = {'period': {'default': 25, 'values': [13,17,19,21,23,25,29,31,34], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category = "Aroon", "Trend"
    def calculate(self, data, params):
        period = params.get('period', 25)
        high, low = data['high'], data['low']
        aroon_up = high.rolling(period + 1).apply(lambda x: (period - x.argmax()) / period * 100, raw=False)
        aroon_down = low.rolling(period + 1).apply(lambda x: (period - x.argmin()) / period * 100, raw=False)
        return pd.DataFrame({'aroon_up': aroon_up, 'aroon_down': aroon_down}, index=data.index)
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = (result['aroon_up'] > result['aroon_down']) & (result['aroon_up'].shift(1) <= result['aroon_down'].shift(1))
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        # TP/SL nur bei Entry setzen, NICHT forward-fillen!
                # Manuelle TP/SL Exit-Logik
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
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': result['aroon_up'] / 100}
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['aroon_up'] > result['aroon_down']) & (result['aroon_up'].shift(1) <= result['aroon_down'].shift(1))
        exits = (result['aroon_down'] > result['aroon_up']) & (result['aroon_down'].shift(1) <= result['aroon_up'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('aroon_cross', index=data.index), 'signal_strength': result['aroon_up'] / 100}
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['aroon_up'], features['aroon_down'], features['aroon_diff'] = result['aroon_up'], result['aroon_down'], result['aroon_up'] - result['aroon_down']
        return features
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
