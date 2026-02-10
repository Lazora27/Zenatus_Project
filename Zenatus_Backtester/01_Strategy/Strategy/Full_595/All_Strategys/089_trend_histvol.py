"""089 - Historical Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HistoricalVolatility:
    """Historical Volatility - Standard Deviation of Returns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'annualize': {'default': 252, 'values': [252], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HistoricalVolatility", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        annualize = params.get('annualize', 252)
        
        # Log returns
        log_returns = np.log(data['close'] / data['close'].shift(1))
        
        # Historical Volatility (annualized)
        hist_vol = log_returns.rolling(period).std() * np.sqrt(annualize) * 100
        
        return hist_vol.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        hist_vol = self.calculate(data, params)
        # Entry when volatility is low (< 20th percentile)
        vol_threshold = hist_vol.rolling(100).quantile(0.2)
        entries = (hist_vol < vol_threshold) & (hist_vol.shift(1) >= vol_threshold.shift(1))
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 
                'signal_strength': (1 / (hist_vol + 1)).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        hist_vol = self.calculate(data, params)
        vol_threshold_low = hist_vol.rolling(100).quantile(0.2)
        vol_threshold_high = hist_vol.rolling(100).quantile(0.8)
        entries = (hist_vol < vol_threshold_low) & (hist_vol.shift(1) >= vol_threshold_low.shift(1))
        exits = (hist_vol > vol_threshold_high) & (hist_vol.shift(1) <= vol_threshold_high.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_vol', index=data.index),
                'signal_strength': (1 / (hist_vol + 1)).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        hist_vol = self.calculate(data, params)
        return pd.DataFrame({'histvol_value': hist_vol, 'histvol_slope': hist_vol.diff(),
                           'histvol_percentile': hist_vol.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x)),
                           'histvol_low': (hist_vol < hist_vol.rolling(100).quantile(0.2)).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
