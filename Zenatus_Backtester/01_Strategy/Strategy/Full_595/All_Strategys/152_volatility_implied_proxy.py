"""152 - Implied Volatility Proxy"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ImpliedVolatilityProxy:
    """Implied Volatility Proxy - ATR-based IV Estimation"""
    PARAMETERS = {
        'atr_period': {'default': 14, 'values': [7,11,13,14,17,19,21,23], 'optimize': True},
        'lookback': {'default': 30, 'values': [20,25,30,34,41,55], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ImpliedVolatilityProxy", "Volatility", __version__
    
    def calculate(self, data, params):
        atr_period = params.get('atr_period', 14)
        lookback = params.get('lookback', 30)
        
        # True Range
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/atr_period, min_periods=atr_period, adjust=False).mean()
        
        # Implied Vol Proxy = ATR / Price * sqrt(252) * 100
        iv_proxy = (atr / close) * np.sqrt(252) * 100
        
        # IV Percentile Rank
        iv_rank = iv_proxy.rolling(lookback).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # IV Mean Reversion Signal
        iv_ma = iv_proxy.rolling(lookback).mean()
        iv_std = iv_proxy.rolling(lookback).std()
        
        return pd.DataFrame({
            'iv_proxy': iv_proxy,
            'iv_rank': iv_rank,
            'iv_ma': iv_ma,
            'iv_std': iv_std
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        iv_data = self.calculate(data, params)
        
        # Entry when IV is low (< 30th percentile)
        entries = (iv_data['iv_rank'] < 0.3) & (iv_data['iv_rank'].shift(1) >= 0.3)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        signal_strength = (1 - iv_data['iv_rank']).clip(0, 1)
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': signal_strength}
    
    def generate_signals_dynamic(self, data, params):
        iv_data = self.calculate(data, params)
        entries = (iv_data['iv_rank'] < 0.3) & (iv_data['iv_rank'].shift(1) >= 0.3)
        exits = (iv_data['iv_rank'] > 0.7) & (iv_data['iv_rank'].shift(1) <= 0.7)
        signal_strength = (1 - iv_data['iv_rank']).clip(0, 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_iv', index=data.index),
                'signal_strength': signal_strength}
    
    def get_ml_features(self, data, params):
        iv_data = self.calculate(data, params)
        return pd.DataFrame({
            'iv_proxy': iv_data['iv_proxy'],
            'iv_rank': iv_data['iv_rank'],
            'iv_zscore': (iv_data['iv_proxy'] - iv_data['iv_ma']) / (iv_data['iv_std'] + 1e-10),
            'iv_slope': iv_data['iv_proxy'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
