"""157 - Close-to-Close Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CloseToCloseVolatility:
    """Close-to-Close Volatility - Classical Estimator"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'annualize': {'default': 252, 'values': [252], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CloseToCloseVolatility", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        annualize = params.get('annualize', 252)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Close-to-Close Volatility (Standard Deviation)
        cc_vol = log_returns.rolling(period).std() * np.sqrt(annualize) * 100
        
        # Exponentially weighted volatility
        ewma_vol = log_returns.ewm(span=period).std() * np.sqrt(annualize) * 100
        
        vol_rank = cc_vol.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        vol_ma = cc_vol.rolling(period).mean()
        
        return pd.DataFrame({'cc_vol': cc_vol, 'ewma_vol': ewma_vol, 'vol_rank': vol_rank, 'vol_ma': vol_ma}, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vol_data = self.calculate(data, params)
        entries = (vol_data['vol_rank'] < 0.25) & (vol_data['vol_rank'].shift(1) >= 0.25)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - vol_data['vol_rank']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        vol_data = self.calculate(data, params)
        entries = (vol_data['vol_rank'] < 0.25) & (vol_data['vol_rank'].shift(1) >= 0.25)
        exits = (vol_data['vol_rank'] > 0.75) & (vol_data['vol_rank'].shift(1) <= 0.75)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_cc_vol', index=data.index),
                'signal_strength': (1 - vol_data['vol_rank']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        vol_data = self.calculate(data, params)
        return pd.DataFrame({'cc_vol': vol_data['cc_vol'], 'ewma_vol': vol_data['ewma_vol'],
                           'cc_rank': vol_data['vol_rank'], 'cc_slope': vol_data['cc_vol'].diff(),
                           'vol_regime': (vol_data['vol_rank'] > 0.5).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
