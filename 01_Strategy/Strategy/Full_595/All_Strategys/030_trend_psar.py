"""030 - Parabolic SAR"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_PSAR:
    """Parabolic SAR - Trend Following"""
    PARAMETERS = {'af_start': {'default': 0.02, 'values': [0.01,0.02,0.03], 'optimize': True}, 'af_increment': {'default': 0.02, 'values': [0.01,0.02,0.03], 'optimize': True}, 'af_max': {'default': 0.2, 'values': [0.1,0.2,0.3], 'optimize': True}, 'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True}, 'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}}
    def __init__(self): self.name, self.category = "PSAR", "Trend"
    
    def calculate(self, data, params):
        af_start, af_inc, af_max = params.get('af_start', 0.02), params.get('af_increment', 0.02), params.get('af_max', 0.2)
        high, low, close = data['high'], data['low'], data['close']
        psar, trend = pd.Series(close.iloc[0], index=data.index), pd.Series(1, index=data.index)
        af, ep = af_start, high.iloc[0]
        
        for i in range(1, len(data)):
            if trend.iloc[i-1] == 1:  # Uptrend
                psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
                if low.iloc[i] < psar.iloc[i]:
                    trend.iloc[i], psar.iloc[i], af, ep = -1, ep, af_start, low.iloc[i]
                else:
                    trend.iloc[i] = 1
                    if high.iloc[i] > ep:
                        ep, af = high.iloc[i], min(af + af_inc, af_max)
            else:  # Downtrend
                psar.iloc[i] = psar.iloc[i-1] - af * (psar.iloc[i-1] - ep)
                if high.iloc[i] > psar.iloc[i]:
                    trend.iloc[i], psar.iloc[i], af, ep = 1, ep, af_start, high.iloc[i]
                else:
                    trend.iloc[i] = -1
                    if low.iloc[i] < ep:
                        ep, af = low.iloc[i], min(af + af_inc, af_max)
        
        return pd.DataFrame({'psar': psar, 'trend': trend}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = (result['trend'] == 1) & (result['trend'].shift(1) == -1)
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
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': abs(data['close'] - result['psar']) / data['close']}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['trend'] == 1) & (result['trend'].shift(1) == -1)
        exits = (result['trend'] == -1) & (result['trend'].shift(1) == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('psar_reverse', index=data.index), 'signal_strength': abs(data['close'] - result['psar']) / data['close']}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['psar_value'], features['psar_trend'] = result['psar'], result['trend']
        features['distance_from_psar'] = data['close'] - result['psar']
        return features
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
