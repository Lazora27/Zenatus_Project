"""112 - Trend Vigor"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TrendVigor:
    """Trend Vigor - Trend strength indicator"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TrendVigor", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate typical price
        typical = (data['high'] + data['low'] + data['close']) / 3
        
        # Calculate price change
        price_change = typical.diff()
        
        # Calculate absolute price change
        abs_change = abs(price_change)
        
        # Trend Vigor = Sum of price changes / Sum of absolute changes
        sum_change = price_change.rolling(period).sum()
        sum_abs_change = abs_change.rolling(period).sum()
        
        vigor = (sum_change / (sum_abs_change + 1e-10)).fillna(0)
        
        # Signal line (EMA of vigor)
        signal = vigor.ewm(span=5).mean()
        
        return pd.DataFrame({'vigor': vigor, 'signal': signal}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when vigor crosses above signal
        entries = (result['vigor'] > result['signal']) & (result['vigor'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['vigor'] - result['signal'])}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['vigor'] > result['signal']) & (result['vigor'].shift(1) <= result['signal'].shift(1))
        exits = (result['vigor'] < result['signal']) & (result['vigor'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('vigor_cross', index=data.index),
                'signal_strength': abs(result['vigor'] - result['signal'])}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'vigor_value': result['vigor'], 'vigor_signal': result['signal'],
                           'vigor_divergence': result['vigor'] - result['signal'],
                           'vigor_positive': (result['vigor'] > 0).astype(int),
                           'vigor_strong': (abs(result['vigor']) > 0.5).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
