"""277 - Chart Patterns"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ChartPatterns:
    """Chart Patterns - Head & Shoulders, Double Top/Bottom, etc."""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tolerance': {'default': 0.02, 'values': [0.01,0.02,0.03], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ChartPatterns", "Patterns", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        tolerance = params.get('tolerance', 0.02)
        high, low, close = data['high'], data['low'], data['close']
        
        # Find peaks and troughs
        peaks = (high > high.shift(1)) & (high > high.shift(-1))
        troughs = (low < low.shift(1)) & (low < low.shift(-1))
        
        # Double Top
        peak_values = high.where(peaks)
        double_top = pd.Series(0, index=data.index)
        for i in range(period, len(data)):
            recent_peaks = peak_values.iloc[i-period:i].dropna()
            if len(recent_peaks) >= 2:
                last_two = recent_peaks.tail(2).values
                if abs(last_two[0] - last_two[1]) / last_two[0] < tolerance:
                    double_top.iloc[i] = 1
        
        # Double Bottom
        trough_values = low.where(troughs)
        double_bottom = pd.Series(0, index=data.index)
        for i in range(period, len(data)):
            recent_troughs = trough_values.iloc[i-period:i].dropna()
            if len(recent_troughs) >= 2:
                last_two = recent_troughs.tail(2).values
                if abs(last_two[0] - last_two[1]) / last_two[0] < tolerance:
                    double_bottom.iloc[i] = 1
        
        # Head and Shoulders (simplified)
        head_shoulders = pd.Series(0, index=data.index)
        for i in range(period*2, len(data)):
            recent_peaks = peak_values.iloc[i-period*2:i].dropna()
            if len(recent_peaks) >= 3:
                last_three = recent_peaks.tail(3).values
                # Middle peak higher than shoulders
                if last_three[1] > last_three[0] and last_three[1] > last_three[2]:
                    if abs(last_three[0] - last_three[2]) / last_three[0] < tolerance:
                        head_shoulders.iloc[i] = 1
        
        # Triangle (converging highs and lows)
        triangle = pd.Series(0, index=data.index)
        high_slope = high.rolling(period).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=False)
        low_slope = low.rolling(period).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=False)
        triangle = ((high_slope < 0) & (low_slope > 0)).astype(int)
        
        # Bullish patterns
        bullish_patterns = double_bottom
        
        # Bearish patterns
        bearish_patterns = double_top + head_shoulders
        
        return pd.DataFrame({
            'double_top': double_top,
            'double_bottom': double_bottom,
            'head_shoulders': head_shoulders,
            'triangle': triangle,
            'bullish_patterns': bullish_patterns,
            'bearish_patterns': bearish_patterns
        }, index=data.index)
    
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
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': pattern_data['bullish_patterns'].clip(0, 2)/2}
    
    def generate_signals_dynamic(self, data, params):
        pattern_data = self.calculate(data, params)
        entries = (pattern_data['bullish_patterns'] > 0) & (data['close'] > data['close'].shift(1))
        exits = (pattern_data['bearish_patterns'] > 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_pattern', index=data.index),
                'signal_strength': pattern_data['bullish_patterns'].clip(0, 2)/2}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
