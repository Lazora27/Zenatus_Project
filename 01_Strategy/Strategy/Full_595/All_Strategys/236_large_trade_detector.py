"""236 - Large Trade Detector"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_LargeTradeDetector:
    """Large Trade Detector - Identifies Unusually Large Trades"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'threshold': {'default': 2.5, 'values': [2.0,2.5,3.0,3.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "LargeTradeDetector", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 2.5)
        volume = data['volume']
        
        # Volume Statistics
        vol_ma = volume.rolling(period).mean()
        vol_std = volume.rolling(period).std()
        
        # Z-Score
        vol_zscore = (volume - vol_ma) / (vol_std + 1e-10)
        
        # Large Trade Detection
        large_trade = (vol_zscore > threshold).astype(int)
        
        # Large Trade Frequency
        large_trade_freq = large_trade.rolling(period).sum()
        
        # Large Trade Cluster
        large_trade_cluster = (large_trade_freq >= 3).astype(int)
        
        # Trade Size Ratio
        trade_size_ratio = volume / vol_ma
        
        return pd.DataFrame({
            'vol_zscore': vol_zscore,
            'large_trade': large_trade,
            'large_trade_freq': large_trade_freq,
            'large_trade_cluster': large_trade_cluster,
            'trade_size_ratio': trade_size_ratio
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ltd_data = self.calculate(data, params)
        entries = (ltd_data['large_trade'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': ltd_data['vol_zscore'].clip(0, 5)/5}
    
    def generate_signals_dynamic(self, data, params):
        ltd_data = self.calculate(data, params)
        entries = (ltd_data['large_trade'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (ltd_data['vol_zscore'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('normal_volume', index=data.index),
                'signal_strength': ltd_data['vol_zscore'].clip(0, 5)/5}
    
    def get_ml_features(self, data, params):
        ltd_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_zscore': ltd_data['vol_zscore'],
            'large_trade': ltd_data['large_trade'],
            'large_trade_freq': ltd_data['large_trade_freq'],
            'large_trade_cluster': ltd_data['large_trade_cluster'],
            'trade_size_ratio': ltd_data['trade_size_ratio']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
