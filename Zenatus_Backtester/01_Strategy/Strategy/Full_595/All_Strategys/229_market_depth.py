"""229 - Market Depth"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MarketDepth:
    """Market Depth - Liquidity Analysis (Approximation)"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MarketDepth", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Depth Approximation (using volume and range)
        price_range = high - low
        depth_proxy = volume / (price_range + 1e-10)
        
        # Depth MA
        depth_ma = depth_proxy.rolling(period).mean()
        
        # Relative Depth
        relative_depth = depth_proxy / (depth_ma + 1e-10)
        
        # High/Low Depth
        high_depth = (relative_depth > 1.5).astype(int)
        low_depth = (relative_depth < 0.7).astype(int)
        
        # Depth Trend
        depth_trend = (depth_proxy > depth_ma).astype(int)
        
        # Depth Volatility
        depth_volatility = depth_proxy.rolling(period).std()
        
        # Liquidity Score
        liquidity_score = (depth_proxy - depth_proxy.rolling(100).min()) / (
            depth_proxy.rolling(100).max() - depth_proxy.rolling(100).min() + 1e-10
        )
        
        return pd.DataFrame({
            'depth_proxy': depth_proxy,
            'depth_ma': depth_ma,
            'relative_depth': relative_depth,
            'high_depth': high_depth,
            'low_depth': low_depth,
            'depth_trend': depth_trend,
            'liquidity_score': liquidity_score
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        md_data = self.calculate(data, params)
        entries = (md_data['high_depth'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': md_data['liquidity_score']}
    
    def generate_signals_dynamic(self, data, params):
        md_data = self.calculate(data, params)
        entries = (md_data['high_depth'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (md_data['low_depth'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('low_depth', index=data.index),
                'signal_strength': md_data['liquidity_score']}
    
    def get_ml_features(self, data, params):
        md_data = self.calculate(data, params)
        return pd.DataFrame({
            'relative_depth': md_data['relative_depth'],
            'high_depth': md_data['high_depth'],
            'low_depth': md_data['low_depth'],
            'depth_trend': md_data['depth_trend'],
            'liquidity_score': md_data['liquidity_score']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
