"""160 - Volatility Index"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolatilityIndex:
    """Volatility Index - Composite Volatility Measure"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'atr_weight': {'default': 0.4, 'values': [0.2,0.3,0.4,0.5,0.6], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolatilityIndex", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        atr_weight = params.get('atr_weight', 0.4)
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Component 1: ATR-based volatility
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        atr_vol = (atr / close) * 100
        
        # Component 2: Close-to-Close volatility
        log_returns = np.log(close / close.shift(1))
        cc_vol = log_returns.rolling(period).std() * np.sqrt(252) * 100
        
        # Component 3: High-Low range volatility
        hl_range = (high - low) / close * 100
        hl_vol = hl_range.rolling(period).mean()
        
        # Composite Volatility Index
        vol_index = (atr_weight * atr_vol + 
                    (1 - atr_weight) * 0.5 * cc_vol + 
                    (1 - atr_weight) * 0.5 * hl_vol)
        
        # Percentile rank
        vol_rank = vol_index.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Moving average
        vol_ma = vol_index.rolling(period).mean()
        vol_std = vol_index.rolling(period).std()
        
        return pd.DataFrame({
            'vol_index': vol_index,
            'vol_rank': vol_rank,
            'vol_ma': vol_ma,
            'vol_std': vol_std,
            'atr_component': atr_vol,
            'cc_component': cc_vol
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vol_data = self.calculate(data, params)
        entries = (vol_data['vol_rank'] < 0.3) & (vol_data['vol_index'] > vol_data['vol_index'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - vol_data['vol_rank']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        vol_data = self.calculate(data, params)
        entries = (vol_data['vol_rank'] < 0.3) & (vol_data['vol_index'] > vol_data['vol_index'].shift(1))
        exits = (vol_data['vol_rank'] > 0.7) | (vol_data['vol_index'] < vol_data['vol_ma'])
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_vol_index', index=data.index),
                'signal_strength': (1 - vol_data['vol_rank']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        vol_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_index': vol_data['vol_index'],
            'vol_rank': vol_data['vol_rank'],
            'vol_zscore': (vol_data['vol_index'] - vol_data['vol_ma']) / (vol_data['vol_std'] + 1e-10),
            'vol_slope': vol_data['vol_index'].diff(),
            'atr_component': vol_data['atr_component'],
            'cc_component': vol_data['cc_component']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
