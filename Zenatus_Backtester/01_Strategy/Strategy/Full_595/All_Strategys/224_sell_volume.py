"""224 - Sell Volume"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SellVolume:
    """Sell Volume - Estimated Selling Pressure Volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SellVolume", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Estimate Sell Volume (inverse of close position)
        close_position = (close - low) / (high - low + 1e-10)
        sell_volume = (1 - close_position) * volume
        
        # Sell Volume MA
        sell_vol_ma = sell_volume.rolling(period).mean()
        
        # Sell Volume Ratio
        sell_vol_ratio = sell_volume / (volume + 1e-10)
        
        # Cumulative Sell Volume
        cumulative_sell = sell_volume.rolling(period).sum()
        
        # Sell Pressure Strength
        sell_strength = (sell_volume > sell_vol_ma * 1.2).astype(int)
        
        # Sell Dominance
        sell_dominance = (sell_vol_ratio > 0.6).astype(int)
        
        # Selling Exhaustion
        exhaustion = (sell_dominance.rolling(5).sum() >= 4).astype(int)
        
        return pd.DataFrame({
            'sell_volume': sell_volume,
            'sell_vol_ma': sell_vol_ma,
            'sell_vol_ratio': sell_vol_ratio,
            'cumulative_sell': cumulative_sell,
            'sell_strength': sell_strength,
            'sell_dominance': sell_dominance,
            'exhaustion': exhaustion
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        sv_data = self.calculate(data, params)
        # Entry bei Selling Exhaustion (Reversal)
        entries = (sv_data['exhaustion'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - sv_data['sell_vol_ratio']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        sv_data = self.calculate(data, params)
        entries = (sv_data['exhaustion'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (sv_data['sell_vol_ratio'] < 0.3)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('buy_pressure', index=data.index),
                'signal_strength': (1 - sv_data['sell_vol_ratio']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        sv_data = self.calculate(data, params)
        return pd.DataFrame({
            'sell_vol_ratio': sv_data['sell_vol_ratio'],
            'cumulative_sell': sv_data['cumulative_sell'],
            'sell_strength': sv_data['sell_strength'],
            'sell_dominance': sv_data['sell_dominance'],
            'exhaustion': sv_data['exhaustion']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
