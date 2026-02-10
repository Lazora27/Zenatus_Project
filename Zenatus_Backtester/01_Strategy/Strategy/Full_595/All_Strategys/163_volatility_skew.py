"""163 - Volatility Skew"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolatilitySkew:
    """Volatility Skew - Asymmetric Vol Distribution"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 0.5, 'values': [0.3,0.5,0.7,1.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolatilitySkew", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Upside volatility (positive returns only)
        upside_returns = log_returns.clip(lower=0)
        upside_vol = upside_returns.rolling(period).std() * np.sqrt(252) * 100
        
        # Downside volatility (negative returns only)
        downside_returns = log_returns.clip(upper=0)
        downside_vol = downside_returns.rolling(period).std() * np.sqrt(252) * 100
        
        # Volatility Skew = Downside Vol / Upside Vol
        vol_skew = downside_vol / (upside_vol + 1e-10)
        
        # Skew ratio (normalized)
        skew_ratio = (vol_skew - 1.0) * 100
        
        # Statistical skewness
        stat_skew = log_returns.rolling(period).skew()
        
        # Skew momentum
        skew_momentum = vol_skew.diff()
        
        return pd.DataFrame({
            'upside_vol': upside_vol,
            'downside_vol': downside_vol,
            'vol_skew': vol_skew,
            'skew_ratio': skew_ratio,
            'stat_skew': stat_skew,
            'skew_momentum': skew_momentum
        }, index=data.index).fillna(1.0)
    
    def generate_signals_fixed(self, data, params):
        skew_data = self.calculate(data, params)
        threshold = params.get('threshold', 0.5)
        # Entry when skew is low (balanced vol) - stable market
        entries = (abs(skew_data['skew_ratio']) < threshold) & (abs(skew_data['skew_ratio'].shift(1)) >= threshold)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 / (abs(skew_data['skew_ratio']) + 1)).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        skew_data = self.calculate(data, params)
        threshold = params.get('threshold', 0.5)
        entries = (abs(skew_data['skew_ratio']) < threshold) & (abs(skew_data['skew_ratio'].shift(1)) >= threshold)
        exits = (abs(skew_data['skew_ratio']) > threshold * 2) & (abs(skew_data['skew_ratio'].shift(1)) <= threshold * 2)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_vol_skew', index=data.index),
                'signal_strength': (1 / (abs(skew_data['skew_ratio']) + 1)).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        skew_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_skew': skew_data['vol_skew'],
            'skew_ratio': skew_data['skew_ratio'],
            'stat_skew': skew_data['stat_skew'],
            'skew_momentum': skew_data['skew_momentum'],
            'downside_bias': (skew_data['vol_skew'] > 1.2).astype(int),
            'upside_bias': (skew_data['vol_skew'] < 0.8).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
