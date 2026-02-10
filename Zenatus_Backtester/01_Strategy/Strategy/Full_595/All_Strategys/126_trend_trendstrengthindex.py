"""126 - Trend Strength Index"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TrendStrengthIndex:
    """Trend Strength Index - Composite trend strength measure"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TrendStrengthIndex", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Component 1: Directional Movement
        high_diff = data['high'].diff()
        low_diff = -data['low'].diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # True Range
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift(1))
        tr3 = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smooth
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / (atr + 1e-10))
        minus_di = 100 * (minus_dm.rolling(period).mean() / (atr + 1e-10))
        
        # Component 2: Price Position
        price_pos = (data['close'] - data['close'].rolling(period).min()) / \
                   (data['close'].rolling(period).max() - data['close'].rolling(period).min() + 1e-10)
        
        # Component 3: Momentum
        momentum = data['close'].pct_change(period)
        momentum_norm = (momentum - momentum.rolling(100).min()) / \
                       (momentum.rolling(100).max() - momentum.rolling(100).min() + 1e-10)
        
        # Trend Strength Index (0-100)
        dx = abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10) * 100
        tsi = (dx * 0.4 + price_pos * 100 * 0.3 + momentum_norm * 100 * 0.3).fillna(50)
        
        return tsi.clip(0, 100)
    
    def generate_signals_fixed(self, data, params):
        tsi = self.calculate(data, params)
        # Entry when TSI crosses above 50 (strong trend)
        entries = (tsi > 50) & (tsi.shift(1) <= 50)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': tsi / 100}
    
    def generate_signals_dynamic(self, data, params):
        tsi = self.calculate(data, params)
        entries = (tsi > 50) & (tsi.shift(1) <= 50)
        exits = (tsi < 40) & (tsi.shift(1) >= 40)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('tsi_weak', index=data.index),
                'signal_strength': tsi / 100}
    
    def get_ml_features(self, data, params):
        tsi = self.calculate(data, params)
        return pd.DataFrame({'tsi_value': tsi, 'tsi_slope': tsi.diff(),
                           'tsi_strong': (tsi > 60).astype(int),
                           'tsi_weak': (tsi < 40).astype(int),
                           'tsi_normalized': tsi / 100}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
