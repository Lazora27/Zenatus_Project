"""158 - Realized Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RealizedVolatility:
    """Realized Volatility - Sum of Squared Returns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'intraday_bars': {'default': 48, 'values': [24,48,96], 'optimize': False},
        'annualize': {'default': 252, 'values': [252], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RealizedVolatility", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        annualize = params.get('annualize', 252)
        intraday = params.get('intraday_bars', 48)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Realized Volatility = sqrt(sum of squared returns)
        rv = np.sqrt((log_returns ** 2).rolling(period).sum()) * np.sqrt(annualize / period) * 100
        
        # Bipower Variation (robust to jumps)
        abs_returns = log_returns.abs()
        bpv = np.sqrt(np.pi / 2) * (abs_returns * abs_returns.shift(1)).rolling(period).sum()
        bpv = np.sqrt(bpv) * np.sqrt(annualize / period) * 100
        
        # Jump component
        jump_component = (rv - bpv).clip(lower=0)
        
        vol_rank = rv.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        vol_ma = rv.rolling(period).mean()
        
        return pd.DataFrame({'rv': rv, 'bpv': bpv, 'jump': jump_component, 'vol_rank': vol_rank, 'vol_ma': vol_ma}, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vol_data = self.calculate(data, params)
        entries = (vol_data['vol_rank'] < 0.3) & (vol_data['jump'] < vol_data['jump'].rolling(20).mean())
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
        entries = (vol_data['vol_rank'] < 0.3) & (vol_data['jump'] < vol_data['jump'].rolling(20).mean())
        exits = (vol_data['vol_rank'] > 0.7) | (vol_data['jump'] > vol_data['jump'].rolling(20).mean() * 2)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_rv_or_jump', index=data.index),
                'signal_strength': (1 - vol_data['vol_rank']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        vol_data = self.calculate(data, params)
        return pd.DataFrame({'rv': vol_data['rv'], 'bpv': vol_data['bpv'], 'jump_component': vol_data['jump'],
                           'rv_rank': vol_data['vol_rank'], 'rv_slope': vol_data['rv'].diff(),
                           'jump_ratio': vol_data['jump'] / (vol_data['rv'] + 1e-10)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
