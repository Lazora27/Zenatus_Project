"""161 - Volatility Cone"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolatilityCone:
    """Volatility Cone - Historical Vol Distribution by Horizon"""
    PARAMETERS = {
        'periods': {'default': [5,10,20,30,60], 'values': [[5,10,20,30,60]], 'optimize': False},
        'percentiles': {'default': [10,25,50,75,90], 'values': [[10,25,50,75,90]], 'optimize': False},
        'lookback': {'default': 252, 'values': [126,252,504], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolatilityCone", "Volatility", __version__
    
    def calculate(self, data, params):
        periods = params.get('periods', [5,10,20,30,60])
        percentiles = params.get('percentiles', [10,25,50,75,90])
        lookback = params.get('lookback', 252)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Calculate realized vol for each period
        vol_20 = log_returns.rolling(20).std() * np.sqrt(252) * 100
        
        # Percentile bands for 20-day vol
        vol_10p = vol_20.rolling(lookback).quantile(0.10)
        vol_25p = vol_20.rolling(lookback).quantile(0.25)
        vol_50p = vol_20.rolling(lookback).quantile(0.50)
        vol_75p = vol_20.rolling(lookback).quantile(0.75)
        vol_90p = vol_20.rolling(lookback).quantile(0.90)
        
        # Current vol position in cone
        vol_percentile = vol_20.rolling(lookback).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Cone width (90p - 10p)
        cone_width = vol_90p - vol_10p
        
        return pd.DataFrame({
            'vol_current': vol_20,
            'vol_10p': vol_10p,
            'vol_25p': vol_25p,
            'vol_50p': vol_50p,
            'vol_75p': vol_75p,
            'vol_90p': vol_90p,
            'vol_percentile': vol_percentile,
            'cone_width': cone_width
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        cone_data = self.calculate(data, params)
        # Entry when vol is below 25th percentile (low vol regime)
        entries = (cone_data['vol_current'] < cone_data['vol_25p']) & (cone_data['vol_current'].shift(1) >= cone_data['vol_25p'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - cone_data['vol_percentile']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        cone_data = self.calculate(data, params)
        entries = (cone_data['vol_current'] < cone_data['vol_25p']) & (cone_data['vol_current'].shift(1) >= cone_data['vol_25p'].shift(1))
        exits = (cone_data['vol_current'] > cone_data['vol_75p']) & (cone_data['vol_current'].shift(1) <= cone_data['vol_75p'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_vol_cone', index=data.index),
                'signal_strength': (1 - cone_data['vol_percentile']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        cone_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_percentile': cone_data['vol_percentile'],
            'cone_width': cone_data['cone_width'],
            'vol_zscore': (cone_data['vol_current'] - cone_data['vol_50p']) / (cone_data['cone_width'] + 1e-10),
            'below_median': (cone_data['vol_current'] < cone_data['vol_50p']).astype(int),
            'extreme_low': (cone_data['vol_current'] < cone_data['vol_10p']).astype(int),
            'extreme_high': (cone_data['vol_current'] > cone_data['vol_90p']).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
