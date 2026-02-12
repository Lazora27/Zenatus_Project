"""167 - EWMA Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_EWMAVolatility:
    """EWMA Volatility - Exponentially Weighted Moving Average"""
    PARAMETERS = {
        'span': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'lambda_param': {'default': 0.94, 'values': [0.9,0.94,0.97,0.99], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "EWMAVolatility", "Volatility", __version__
    
    def calculate(self, data, params):
        span = params.get('span', 20)
        lambda_param = params.get('lambda_param', 0.94)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # EWMA Volatility (RiskMetrics style)
        ewma_var = (log_returns ** 2).ewm(span=span, adjust=False).mean()
        ewma_vol = np.sqrt(ewma_var) * np.sqrt(252) * 100
        
        # Alternative: Lambda-based EWMA
        lambda_var = (log_returns ** 2).ewm(alpha=1-lambda_param, adjust=False).mean()
        lambda_vol = np.sqrt(lambda_var) * np.sqrt(252) * 100
        
        # EWMA of absolute returns (alternative measure)
        ewma_abs = log_returns.abs().ewm(span=span, adjust=False).mean() * np.sqrt(252) * 100
        
        # Vol rank
        vol_rank = ewma_vol.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Vol momentum
        vol_momentum = ewma_vol.diff()
        
        return pd.DataFrame({
            'ewma_vol': ewma_vol,
            'lambda_vol': lambda_vol,
            'ewma_abs': ewma_abs,
            'vol_rank': vol_rank,
            'vol_momentum': vol_momentum
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ewma_data = self.calculate(data, params)
        # Entry when EWMA vol is low and rising
        entries = (ewma_data['vol_rank'] < 0.3) & (ewma_data['vol_momentum'] > 0)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - ewma_data['vol_rank']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        ewma_data = self.calculate(data, params)
        entries = (ewma_data['vol_rank'] < 0.3) & (ewma_data['vol_momentum'] > 0)
        exits = (ewma_data['vol_rank'] > 0.7) | (ewma_data['vol_momentum'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_ewma_vol', index=data.index),
                'signal_strength': (1 - ewma_data['vol_rank']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        ewma_data = self.calculate(data, params)
        return pd.DataFrame({
            'ewma_vol': ewma_data['ewma_vol'],
            'lambda_vol': ewma_data['lambda_vol'],
            'vol_rank': ewma_data['vol_rank'],
            'vol_momentum': ewma_data['vol_momentum'],
            'vol_acceleration': ewma_data['vol_momentum'].diff(),
            'vol_divergence': ewma_data['ewma_vol'] - ewma_data['lambda_vol']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
