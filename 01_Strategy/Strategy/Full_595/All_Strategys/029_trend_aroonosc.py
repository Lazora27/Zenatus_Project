"""029 - Aroon Oscillator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_AroonOsc:
    """Aroon Oscillator - Trend Strength"""
    PARAMETERS = {'period': {'default': 25, 'values': [13,17,19,21,23,25,29,31], 'optimize': True}, 'threshold': {'default': 0, 'values': [-50,-25,0,25,50], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category = "AroonOsc", "Trend"
    def calculate(self, data, params):
        period = params.get('period', 25)
        high, low = data['high'], data['low']
        aroon_up = high.rolling(period + 1).apply(lambda x: (period - x.argmax()) / period * 100, raw=False)
        aroon_down = low.rolling(period + 1).apply(lambda x: (period - x.argmin()) / period * 100, raw=False)
        aroon_osc = aroon_up - aroon_down
        return aroon_osc
    def generate_signals_fixed(self, data, params):
        aroon_osc = self.calculate(data, params)
        threshold = params.get('threshold', 0)
        entries = (aroon_osc > threshold) & (aroon_osc.shift(1) <= threshold)
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
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': abs(aroon_osc) / 100}
    def generate_signals_dynamic(self, data, params):
        aroon_osc = self.calculate(data, params)
        threshold = params.get('threshold', 0)
        entries = (aroon_osc > threshold) & (aroon_osc.shift(1) <= threshold)
        exits = (aroon_osc < -threshold) & (aroon_osc.shift(1) >= -threshold)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('aroonosc_reverse', index=data.index), 'signal_strength': abs(aroon_osc) / 100}
    def get_ml_features(self, data, params):
        aroon_osc = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['aroonosc_value'], features['aroonosc_slope'] = aroon_osc, aroon_osc.diff()
        return features
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
