"""097 - Parabolic SAR Extended"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PSARExtended:
    """Parabolic SAR Extended - Enhanced Stop and Reverse"""
    PARAMETERS = {
        'af_start': {'default': 0.02, 'values': [0.01,0.02,0.03], 'optimize': True},
        'af_increment': {'default': 0.02, 'values': [0.01,0.02,0.03], 'optimize': True},
        'af_max': {'default': 0.2, 'values': [0.15,0.2,0.25,0.3], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PSARExtended", "Trend", __version__
    
    def calculate(self, data, params):
        af_start = params.get('af_start', 0.02)
        af_increment = params.get('af_increment', 0.02)
        af_max = params.get('af_max', 0.2)
        
        # Parabolic SAR
        psar = pd.Series(index=data.index, dtype=float)
        trend = pd.Series(index=data.index, dtype=int)
        af = pd.Series(index=data.index, dtype=float)
        ep = pd.Series(index=data.index, dtype=float)
        
        # Initialize
        psar.iloc[0] = data['low'].iloc[0]
        trend.iloc[0] = 1
        af.iloc[0] = af_start
        ep.iloc[0] = data['high'].iloc[0]
        
        for i in range(1, len(data)):
            if trend.iloc[i-1] == 1:  # Uptrend
                psar.iloc[i] = psar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - psar.iloc[i-1])
                
                if data['low'].iloc[i] < psar.iloc[i]:
                    trend.iloc[i] = -1
                    psar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = data['low'].iloc[i]
                    af.iloc[i] = af_start
                else:
                    trend.iloc[i] = 1
                    if data['high'].iloc[i] > ep.iloc[i-1]:
                        ep.iloc[i] = data['high'].iloc[i]
                        af.iloc[i] = min(af.iloc[i-1] + af_increment, af_max)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        af.iloc[i] = af.iloc[i-1]
            else:  # Downtrend
                psar.iloc[i] = psar.iloc[i-1] - af.iloc[i-1] * (psar.iloc[i-1] - ep.iloc[i-1])
                
                if data['high'].iloc[i] > psar.iloc[i]:
                    trend.iloc[i] = 1
                    psar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = data['high'].iloc[i]
                    af.iloc[i] = af_start
                else:
                    trend.iloc[i] = -1
                    if data['low'].iloc[i] < ep.iloc[i-1]:
                        ep.iloc[i] = data['low'].iloc[i]
                        af.iloc[i] = min(af.iloc[i-1] + af_increment, af_max)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        af.iloc[i] = af.iloc[i-1]
        
        return pd.DataFrame({'psar': psar, 'trend': trend}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = (result['trend'] == 1) & (result['trend'].shift(1) == -1)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 
                'signal_strength': abs(result['trend'])}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['trend'] == 1) & (result['trend'].shift(1) == -1)
        exits = (result['trend'] == -1) & (result['trend'].shift(1) == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('psar_reverse', index=data.index),
                'signal_strength': abs(result['trend'])}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'psar_value': result['psar'], 'psar_trend': result['trend'],
                           'distance_from_psar': data['close'] - result['psar'],
                           'psar_uptrend': (result['trend'] == 1).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
