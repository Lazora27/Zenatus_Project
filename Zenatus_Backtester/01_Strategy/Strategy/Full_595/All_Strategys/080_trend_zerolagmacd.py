"""080 - Zero-Lag MACD"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ZeroLagMACD:
    """Zero-Lag MACD - MACD with reduced lag"""
    PARAMETERS = {
        'fast': {'default': 12, 'values': [8,11,12,13,14,17], 'optimize': True},
        'slow': {'default': 26, 'values': [19,21,23,26,29,31,34], 'optimize': True},
        'signal': {'default': 9, 'values': [5,7,8,9,11,13], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ZeroLagMACD", "Momentum", __version__
    
    def calculate(self, data, params):
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)
        
        # Zero-Lag EMA calculation
        def zero_lag_ema(series, period):
            ema = series.ewm(span=period).mean()
            # Lag reduction
            lag = int((period - 1) / 2)
            if lag > 0:
                ema_lag = ema.shift(lag)
                zero_lag = 2 * ema - ema_lag
                return zero_lag.fillna(ema)
            return ema
        
        # Zero-Lag MACD
        zl_fast = zero_lag_ema(data['close'], fast)
        zl_slow = zero_lag_ema(data['close'], slow)
        zl_macd = zl_fast - zl_slow
        
        # Signal Line
        zl_signal = zl_macd.ewm(span=signal_period).mean()
        
        return pd.DataFrame({'macd': zl_macd.fillna(0), 'signal': zl_signal.fillna(0)}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when MACD crosses above Signal
        entries = (result['macd'] > result['signal']) & (result['macd'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['macd'] - result['signal']).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['macd'] > result['signal']) & (result['macd'].shift(1) <= result['signal'].shift(1))
        exits = (result['macd'] < result['signal']) & (result['macd'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('zlmacd_cross', index=data.index),
                'signal_strength': abs(result['macd'] - result['signal']).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'zlmacd_value': result['macd'], 'zlmacd_signal': result['signal'],
                           'zlmacd_divergence': result['macd'] - result['signal'],
                           'zlmacd_histogram': result['macd'] - result['signal']}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
