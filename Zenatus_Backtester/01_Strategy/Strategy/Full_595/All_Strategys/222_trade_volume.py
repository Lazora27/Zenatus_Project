"""222 - Trade Volume"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TradeVolume:
    """Trade Volume - Actual Traded Volume Analysis"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TradeVolume", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        volume = data['volume']
        
        # Trade Volume Statistics
        trade_vol_ma = volume.rolling(period).mean()
        trade_vol_std = volume.rolling(period).std()
        
        # Z-Score
        trade_vol_zscore = (volume - trade_vol_ma) / (trade_vol_std + 1e-10)
        
        # Volume Percentile
        trade_vol_percentile = volume.rolling(100).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        # Abnormal Volume
        abnormal_high = (trade_vol_zscore > 2).astype(int)
        abnormal_low = (trade_vol_zscore < -2).astype(int)
        
        # Volume Acceleration
        vol_acceleration = volume.diff().diff()
        
        return pd.DataFrame({
            'trade_volume': volume,
            'trade_vol_ma': trade_vol_ma,
            'trade_vol_zscore': trade_vol_zscore,
            'trade_vol_percentile': trade_vol_percentile,
            'abnormal_high': abnormal_high,
            'abnormal_low': abnormal_low,
            'vol_acceleration': vol_acceleration
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        tv_data = self.calculate(data, params)
        entries = (tv_data['abnormal_high'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': tv_data['trade_vol_percentile']}
    
    def generate_signals_dynamic(self, data, params):
        tv_data = self.calculate(data, params)
        entries = (tv_data['abnormal_high'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (tv_data['abnormal_low'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('abnormal_low_volume', index=data.index),
                'signal_strength': tv_data['trade_vol_percentile']}
    
    def get_ml_features(self, data, params):
        tv_data = self.calculate(data, params)
        return pd.DataFrame({
            'trade_vol_zscore': tv_data['trade_vol_zscore'],
            'trade_vol_percentile': tv_data['trade_vol_percentile'],
            'abnormal_high': tv_data['abnormal_high'],
            'abnormal_low': tv_data['abnormal_low'],
            'vol_acceleration': tv_data['vol_acceleration']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
