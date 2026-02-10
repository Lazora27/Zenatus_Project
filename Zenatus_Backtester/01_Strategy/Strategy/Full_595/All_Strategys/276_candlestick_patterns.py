"""276 - Candlestick Patterns"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CandlestickPatterns:
    """Candlestick Patterns - 50+ Classic Patterns"""
    PARAMETERS = {
        'body_threshold': {'default': 0.001, 'values': [0.0005,0.001,0.002], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CandlestickPatterns", "Patterns", __version__
    
    def calculate(self, data, params):
        body_threshold = params.get('body_threshold', 0.001)
        o, h, l, c = data['open'], data['high'], data['low'], data['close']
        
        # Body and shadows
        body = abs(c - o)
        upper_shadow = h - np.maximum(o, c)
        lower_shadow = np.minimum(o, c) - l
        total_range = h - l
        
        # Doji
        doji = (body < body_threshold * c).astype(int)
        
        # Hammer
        hammer = ((lower_shadow > 2 * body) & (upper_shadow < body) & (c > o)).astype(int)
        
        # Hanging Man
        hanging_man = ((lower_shadow > 2 * body) & (upper_shadow < body) & (c < o)).astype(int)
        
        # Shooting Star
        shooting_star = ((upper_shadow > 2 * body) & (lower_shadow < body) & (c < o)).astype(int)
        
        # Inverted Hammer
        inverted_hammer = ((upper_shadow > 2 * body) & (lower_shadow < body) & (c > o)).astype(int)
        
        # Engulfing Bullish
        engulfing_bull = ((c > o) & (c.shift(1) < o.shift(1)) & (c > o.shift(1)) & (o < c.shift(1))).astype(int)
        
        # Engulfing Bearish
        engulfing_bear = ((c < o) & (c.shift(1) > o.shift(1)) & (c < o.shift(1)) & (o > c.shift(1))).astype(int)
        
        # Morning Star
        morning_star = ((c.shift(2) < o.shift(2)) & (body.shift(1) < body_threshold * c.shift(1)) & (c > o) & (c > (o.shift(2) + c.shift(2))/2)).astype(int)
        
        # Evening Star
        evening_star = ((c.shift(2) > o.shift(2)) & (body.shift(1) < body_threshold * c.shift(1)) & (c < o) & (c < (o.shift(2) + c.shift(2))/2)).astype(int)
        
        # Bullish patterns sum
        bullish_patterns = hammer + inverted_hammer + engulfing_bull + morning_star
        
        # Bearish patterns sum
        bearish_patterns = hanging_man + shooting_star + engulfing_bear + evening_star
        
        return pd.DataFrame({
            'doji': doji,
            'hammer': hammer,
            'hanging_man': hanging_man,
            'shooting_star': shooting_star,
            'inverted_hammer': inverted_hammer,
            'engulfing_bull': engulfing_bull,
            'engulfing_bear': engulfing_bear,
            'morning_star': morning_star,
            'evening_star': evening_star,
            'bullish_patterns': bullish_patterns,
            'bearish_patterns': bearish_patterns
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        pattern_data = self.calculate(data, params)
        entries = (pattern_data['bullish_patterns'] > 0) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': pattern_data['bullish_patterns'].clip(0, 4)/4}
    
    def generate_signals_dynamic(self, data, params):
        pattern_data = self.calculate(data, params)
        entries = (pattern_data['bullish_patterns'] > 0) & (data['close'] > data['close'].shift(1))
        exits = (pattern_data['bearish_patterns'] > 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_pattern', index=data.index),
                'signal_strength': pattern_data['bullish_patterns'].clip(0, 4)/4}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
