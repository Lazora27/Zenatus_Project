"""164 - Volatility Surface"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolatilitySurface:
    """Volatility Surface - 3D Vol by Time & Moneyness"""
    PARAMETERS = {
        'short_period': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'medium_period': {'default': 20, 'values': [13,17,19,20,21], 'optimize': True},
        'long_period': {'default': 60, 'values': [41,55,60,89], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolatilitySurface", "Volatility", __version__
    
    def calculate(self, data, params):
        short_period = params.get('short_period', 5)
        medium_period = params.get('medium_period', 20)
        long_period = params.get('long_period', 60)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Vol term structure (different time horizons)
        vol_short = log_returns.rolling(short_period).std() * np.sqrt(252) * 100
        vol_medium = log_returns.rolling(medium_period).std() * np.sqrt(252) * 100
        vol_long = log_returns.rolling(long_period).std() * np.sqrt(252) * 100
        
        # Term structure slope
        term_slope = (vol_long - vol_short) / (long_period - short_period)
        
        # Surface curvature
        surface_curve = vol_medium - (vol_short + vol_long) / 2
        
        # Surface twist (interaction of time & moneyness)
        price_ma = close.rolling(medium_period).mean()
        moneyness = (close - price_ma) / price_ma * 100
        surface_twist = term_slope * moneyness
        
        # Surface flatness indicator
        vol_range = vol_long - vol_short
        surface_flat = (vol_range < vol_range.rolling(100).quantile(0.3)).astype(int)
        
        return pd.DataFrame({
            'vol_short': vol_short,
            'vol_medium': vol_medium,
            'vol_long': vol_long,
            'term_slope': term_slope,
            'surface_curve': surface_curve,
            'surface_twist': surface_twist,
            'surface_flat': surface_flat
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        surface_data = self.calculate(data, params)
        # Entry when surface is flat (low term structure slope)
        entries = (surface_data['surface_flat'] == 1) & (surface_data['surface_flat'].shift(1) == 0)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': surface_data['surface_flat'].astype(float)}
    
    def generate_signals_dynamic(self, data, params):
        surface_data = self.calculate(data, params)
        entries = (surface_data['surface_flat'] == 1) & (surface_data['surface_flat'].shift(1) == 0)
        exits = (surface_data['surface_flat'] == 0) & (surface_data['surface_flat'].shift(1) == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('surface_steep', index=data.index),
                'signal_strength': surface_data['surface_flat'].astype(float)}
    
    def get_ml_features(self, data, params):
        surface_data = self.calculate(data, params)
        return pd.DataFrame({
            'term_slope': surface_data['term_slope'],
            'surface_curve': surface_data['surface_curve'],
            'surface_twist': surface_data['surface_twist'],
            'surface_flat': surface_data['surface_flat'],
            'vol_term_ratio': surface_data['vol_short'] / (surface_data['vol_long'] + 1e-10),
            'surface_convexity': surface_data['surface_curve'] / (surface_data['vol_medium'] + 1e-10)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
