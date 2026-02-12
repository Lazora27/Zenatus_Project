"""099 - Price Oscillator (Percentage)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PriceOscillator:
    """Price Oscillator - Percentage difference between two EMAs"""
    PARAMETERS = {
        'fast': {'default': 12, 'values': [8,10,12,14,17], 'optimize': True},
        'slow': {'default': 26, 'values': [20,23,26,29,31,34], 'optimize': True},
        'signal': {'default': 9, 'values': [5,7,9,11,13], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PriceOscillator", "Momentum", __version__
    
    def calculate(self, data, params):
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)
        
        # EMAs
        ema_fast = data['close'].ewm(span=fast).mean()
        ema_slow = data['close'].ewm(span=slow).mean()
        
        # Price Oscillator (Percentage)
        po = ((ema_fast - ema_slow) / ema_slow * 100).fillna(0)
        
        # Signal Line
        signal = po.ewm(span=signal_period).mean()
        
        return pd.DataFrame({'po': po, 'signal': signal}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when PO crosses above signal
        entries = (result['po'] > result['signal']) & (result['po'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['po'] - result['signal']).clip(0, 5) / 5}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['po'] > result['signal']) & (result['po'].shift(1) <= result['signal'].shift(1))
        exits = (result['po'] < result['signal']) & (result['po'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('po_cross', index=data.index),
                'signal_strength': abs(result['po'] - result['signal']).clip(0, 5) / 5}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'po_value': result['po'], 'po_signal': result['signal'],
                           'po_divergence': result['po'] - result['signal'],
                           'po_positive': (result['po'] > 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
