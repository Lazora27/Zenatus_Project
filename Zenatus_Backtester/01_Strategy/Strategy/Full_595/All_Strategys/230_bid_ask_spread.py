"""230 - Bid-Ask Spread"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BidAskSpread:
    """Bid-Ask Spread - Spread Analysis (Approximation)"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BidAskSpread", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close = data['high'], data['low'], data['close']
        
        # Spread Approximation (using high-low)
        spread = high - low
        
        # Relative Spread
        relative_spread = spread / close
        
        # Spread MA
        spread_ma = spread.rolling(period).mean()
        
        # Spread Ratio
        spread_ratio = spread / (spread_ma + 1e-10)
        
        # Wide/Narrow Spread
        wide_spread = (spread_ratio > 1.5).astype(int)
        narrow_spread = (spread_ratio < 0.7).astype(int)
        
        # Spread Volatility
        spread_volatility = spread.rolling(period).std()
        
        # Spread Trend
        spread_trend = (spread > spread.shift(1)).astype(int)
        
        # Normalized Spread
        spread_normalized = (spread - spread.rolling(100).min()) / (
            spread.rolling(100).max() - spread.rolling(100).min() + 1e-10
        )
        
        return pd.DataFrame({
            'spread': spread,
            'relative_spread': relative_spread,
            'spread_ratio': spread_ratio,
            'wide_spread': wide_spread,
            'narrow_spread': narrow_spread,
            'spread_volatility': spread_volatility,
            'spread_normalized': spread_normalized
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        bas_data = self.calculate(data, params)
        # Entry bei Narrow Spread (bessere Liquidität)
        entries = (bas_data['narrow_spread'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - bas_data['spread_normalized']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        bas_data = self.calculate(data, params)
        entries = (bas_data['narrow_spread'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (bas_data['wide_spread'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('wide_spread', index=data.index),
                'signal_strength': (1 - bas_data['spread_normalized']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        bas_data = self.calculate(data, params)
        return pd.DataFrame({
            'relative_spread': bas_data['relative_spread'],
            'spread_ratio': bas_data['spread_ratio'],
            'wide_spread': bas_data['wide_spread'],
            'narrow_spread': bas_data['narrow_spread'],
            'spread_normalized': bas_data['spread_normalized']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
