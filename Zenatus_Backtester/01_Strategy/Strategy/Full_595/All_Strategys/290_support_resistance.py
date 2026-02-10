"""290 - Support/Resistance Levels"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SupportResistance:
    """Support/Resistance Levels - Key Price Levels"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [30,50,100,200], 'optimize': True},
        'tolerance': {'default': 0.01, 'values': [0.005,0.01,0.02], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SupportResistance", "Patterns", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        tolerance = params.get('tolerance', 0.01)
        high, low, close = data['high'], data['low'], data['close']
        
        # Support levels (recent lows)
        support1 = low.rolling(period).min()
        support2 = low.rolling(period*2).quantile(0.25)
        
        # Resistance levels (recent highs)
        resistance1 = high.rolling(period).max()
        resistance2 = high.rolling(period*2).quantile(0.75)
        
        # Current position
        at_support = (abs(close - support1) / close < tolerance).astype(int)
        at_resistance = (abs(close - resistance1) / close < tolerance).astype(int)
        
        # Distance to levels
        distance_to_support = abs(close - support1) / close
        distance_to_resistance = abs(close - resistance1) / close
        
        # Level strength (how often price bounced)
        support_touches = (abs(low - support1) / close < tolerance).rolling(period).sum()
        resistance_touches = (abs(high - resistance1) / close < tolerance).rolling(period).sum()
        
        # Support/Resistance strength
        sr_strength = (support_touches + resistance_touches) / (period * 2)
        
        return pd.DataFrame({
            'support1': support1,
            'support2': support2,
            'resistance1': resistance1,
            'resistance2': resistance2,
            'at_support': at_support,
            'at_resistance': at_resistance,
            'distance_to_support': distance_to_support,
            'distance_to_resistance': distance_to_resistance,
            'support_touches': support_touches,
            'resistance_touches': resistance_touches,
            'sr_strength': sr_strength
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        sr_data = self.calculate(data, params)
        entries = (sr_data['at_support'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': sr_data['sr_strength']}
    
    def generate_signals_dynamic(self, data, params):
        sr_data = self.calculate(data, params)
        entries = (sr_data['at_support'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (sr_data['at_resistance'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('at_resistance', index=data.index),
                'signal_strength': sr_data['sr_strength']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
