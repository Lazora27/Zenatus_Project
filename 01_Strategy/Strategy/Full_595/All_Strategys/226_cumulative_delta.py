"""226 - Cumulative Delta"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CumulativeDelta:
    """Cumulative Delta - Running Sum of Delta Volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CumulativeDelta", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Delta Volume
        close_position = (close - low) / (high - low + 1e-10)
        buy_volume = close_position * volume
        sell_volume = (1 - close_position) * volume
        delta = buy_volume - sell_volume
        
        # Cumulative Delta (running sum)
        cumulative_delta = delta.cumsum()
        
        # Cumulative Delta Slope
        cd_slope = cumulative_delta.diff(period)
        
        # Cumulative Delta MA
        cd_ma = cumulative_delta.rolling(period).mean()
        
        # Above/Below MA
        cd_trend = (cumulative_delta > cd_ma).astype(int)
        
        # Delta Momentum
        delta_momentum = delta.rolling(period).sum()
        
        # Normalized CD
        cd_normalized = (cumulative_delta - cumulative_delta.rolling(100).min()) / (
            cumulative_delta.rolling(100).max() - cumulative_delta.rolling(100).min() + 1e-10
        )
        
        return pd.DataFrame({
            'cumulative_delta': cumulative_delta,
            'cd_slope': cd_slope,
            'cd_ma': cd_ma,
            'cd_trend': cd_trend,
            'delta_momentum': delta_momentum,
            'cd_normalized': cd_normalized
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        cd_data = self.calculate(data, params)
        entries = (cd_data['cumulative_delta'] > cd_data['cd_ma']) & (cd_data['cumulative_delta'].shift(1) <= cd_data['cd_ma'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': cd_data['cd_normalized']}
    
    def generate_signals_dynamic(self, data, params):
        cd_data = self.calculate(data, params)
        entries = (cd_data['cumulative_delta'] > cd_data['cd_ma']) & (cd_data['cumulative_delta'].shift(1) <= cd_data['cd_ma'].shift(1))
        exits = (cd_data['cumulative_delta'] < cd_data['cd_ma']) & (cd_data['cumulative_delta'].shift(1) >= cd_data['cd_ma'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cd_cross_down', index=data.index),
                'signal_strength': cd_data['cd_normalized']}
    
    def get_ml_features(self, data, params):
        cd_data = self.calculate(data, params)
        return pd.DataFrame({
            'cd_slope': cd_data['cd_slope'],
            'cd_trend': cd_data['cd_trend'],
            'delta_momentum': cd_data['delta_momentum'],
            'cd_normalized': cd_data['cd_normalized']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
