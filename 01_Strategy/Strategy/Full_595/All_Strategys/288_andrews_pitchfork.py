"""288 - Andrews Pitchfork"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AndrewsPitchfork:
    """Andrews Pitchfork - Median Line Analysis"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [30,50,100], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AndrewsPitchfork", "Patterns", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        high, low, close = data['high'], data['low'], data['close']
        
        # Find three pivot points (simplified)
        pivot1 = low.rolling(period).min()
        pivot2 = high.rolling(period).max()
        pivot3 = close.rolling(period).mean()
        
        # Median line (from pivot1 through midpoint of pivot2-pivot3)
        median_line = (pivot1 + pivot2 + pivot3) / 3
        
        # Upper and lower parallel lines
        price_range = pivot2 - pivot1
        upper_line = median_line + price_range * 0.5
        lower_line = median_line - price_range * 0.5
        
        # Position relative to pitchfork
        above_median = (close > median_line).astype(int)
        below_median = (close < median_line).astype(int)
        at_upper = (abs(close - upper_line) / close < 0.01).astype(int)
        at_lower = (abs(close - lower_line) / close < 0.01).astype(int)
        
        # Pitchfork zone (0=lower, 1=median, 2=upper)
        pitchfork_zone = pd.Series(1, index=close.index)
        pitchfork_zone[close > upper_line] = 2
        pitchfork_zone[close < lower_line] = 0
        
        return pd.DataFrame({
            'median_line': median_line,
            'upper_line': upper_line,
            'lower_line': lower_line,
            'above_median': above_median,
            'below_median': below_median,
            'at_upper': at_upper,
            'at_lower': at_lower,
            'pitchfork_zone': pitchfork_zone
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ap_data = self.calculate(data, params)
        entries = (ap_data['at_lower'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (ap_data['pitchfork_zone'] / 2)}
    
    def generate_signals_dynamic(self, data, params):
        ap_data = self.calculate(data, params)
        entries = (ap_data['at_lower'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (ap_data['at_upper'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('at_upper_line', index=data.index),
                'signal_strength': (ap_data['pitchfork_zone'] / 2)}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
