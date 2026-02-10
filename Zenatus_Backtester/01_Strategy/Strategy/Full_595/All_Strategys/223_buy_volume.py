"""223 - Buy Volume"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BuyVolume:
    """Buy Volume - Estimated Buying Pressure Volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BuyVolume", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Estimate Buy Volume (close position in range)
        close_position = (close - low) / (high - low + 1e-10)
        buy_volume = close_position * volume
        
        # Buy Volume MA
        buy_vol_ma = buy_volume.rolling(period).mean()
        
        # Buy Volume Ratio
        buy_vol_ratio = buy_volume / (volume + 1e-10)
        
        # Cumulative Buy Volume
        cumulative_buy = buy_volume.rolling(period).sum()
        
        # Buy Pressure Strength
        buy_strength = (buy_volume > buy_vol_ma * 1.2).astype(int)
        
        # Buy Dominance
        buy_dominance = (buy_vol_ratio > 0.6).astype(int)
        
        return pd.DataFrame({
            'buy_volume': buy_volume,
            'buy_vol_ma': buy_vol_ma,
            'buy_vol_ratio': buy_vol_ratio,
            'cumulative_buy': cumulative_buy,
            'buy_strength': buy_strength,
            'buy_dominance': buy_dominance
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        bv_data = self.calculate(data, params)
        entries = (bv_data['buy_dominance'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': bv_data['buy_vol_ratio']}
    
    def generate_signals_dynamic(self, data, params):
        bv_data = self.calculate(data, params)
        entries = (bv_data['buy_dominance'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (bv_data['buy_vol_ratio'] < 0.4)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('sell_dominance', index=data.index),
                'signal_strength': bv_data['buy_vol_ratio']}
    
    def get_ml_features(self, data, params):
        bv_data = self.calculate(data, params)
        return pd.DataFrame({
            'buy_vol_ratio': bv_data['buy_vol_ratio'],
            'cumulative_buy': bv_data['cumulative_buy'],
            'buy_strength': bv_data['buy_strength'],
            'buy_dominance': bv_data['buy_dominance']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
