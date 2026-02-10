"""225 - Delta Volume"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DeltaVolume:
    """Delta Volume - Buy Volume minus Sell Volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DeltaVolume", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Buy/Sell Volume Estimation
        close_position = (close - low) / (high - low + 1e-10)
        buy_volume = close_position * volume
        sell_volume = (1 - close_position) * volume
        
        # Delta Volume
        delta_volume = buy_volume - sell_volume
        
        # Delta Volume MA
        delta_ma = delta_volume.rolling(period).mean()
        
        # Cumulative Delta
        cumulative_delta = delta_volume.rolling(period).sum()
        
        # Delta Trend
        delta_positive = (delta_volume > 0).astype(int)
        delta_trend = (cumulative_delta > 0).astype(int)
        
        # Delta Strength
        delta_strength = abs(delta_volume) / (volume + 1e-10)
        
        # Delta Divergence
        price_change = close.diff(period)
        delta_divergence = ((price_change > 0) & (cumulative_delta < 0)) | ((price_change < 0) & (cumulative_delta > 0))
        
        return pd.DataFrame({
            'delta_volume': delta_volume,
            'delta_ma': delta_ma,
            'cumulative_delta': cumulative_delta,
            'delta_positive': delta_positive,
            'delta_trend': delta_trend,
            'delta_strength': delta_strength,
            'delta_divergence': delta_divergence.astype(int)
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        dv_data = self.calculate(data, params)
        entries = (dv_data['cumulative_delta'] > 0) & (dv_data['cumulative_delta'].shift(1) <= 0)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': dv_data['delta_strength']}
    
    def generate_signals_dynamic(self, data, params):
        dv_data = self.calculate(data, params)
        entries = (dv_data['cumulative_delta'] > 0) & (dv_data['cumulative_delta'].shift(1) <= 0)
        exits = (dv_data['cumulative_delta'] < 0) & (dv_data['cumulative_delta'].shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('delta_reversal', index=data.index),
                'signal_strength': dv_data['delta_strength']}
    
    def get_ml_features(self, data, params):
        dv_data = self.calculate(data, params)
        return pd.DataFrame({
            'delta_volume': dv_data['delta_volume'],
            'cumulative_delta': dv_data['cumulative_delta'],
            'delta_trend': dv_data['delta_trend'],
            'delta_strength': dv_data['delta_strength'],
            'delta_divergence': dv_data['delta_divergence']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
