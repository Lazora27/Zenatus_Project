"""166 - GARCH Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_GARCHVolatility:
    """GARCH Volatility - Generalized Autoregressive Conditional Heteroskedasticity"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'alpha': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': True},
        'beta': {'default': 0.85, 'values': [0.7,0.8,0.85,0.9], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "GARCHVolatility", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        alpha = params.get('alpha', 0.1)
        beta = params.get('beta', 0.85)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Simplified GARCH(1,1): σ²(t) = ω + α*ε²(t-1) + β*σ²(t-1)
        # Initialize with sample variance
        variance = (log_returns.rolling(period).std() ** 2).fillna(0)
        garch_var = variance.copy()
        
        # GARCH iteration (simplified)
        omega = (1 - alpha - beta) * variance.mean()
        for i in range(period, len(log_returns)):
            if i > 0 and not np.isnan(log_returns.iloc[i-1]):
                garch_var.iloc[i] = omega + alpha * (log_returns.iloc[i-1] ** 2) + beta * garch_var.iloc[i-1]
        
        # GARCH volatility (annualized)
        garch_vol = np.sqrt(garch_var) * np.sqrt(252) * 100
        
        # Conditional volatility forecast
        vol_forecast = np.sqrt(omega + alpha * (log_returns ** 2) + beta * garch_var) * np.sqrt(252) * 100
        
        # Volatility persistence
        persistence = alpha + beta
        
        # Vol rank
        vol_rank = garch_vol.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        return pd.DataFrame({
            'garch_vol': garch_vol,
            'vol_forecast': vol_forecast,
            'persistence': pd.Series(persistence, index=data.index),
            'vol_rank': vol_rank
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        garch_data = self.calculate(data, params)
        # Entry when GARCH vol is low (< 30th percentile)
        entries = (garch_data['vol_rank'] < 0.3) & (garch_data['vol_rank'].shift(1) >= 0.3)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 - garch_data['vol_rank']).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        garch_data = self.calculate(data, params)
        entries = (garch_data['vol_rank'] < 0.3) & (garch_data['vol_rank'].shift(1) >= 0.3)
        exits = (garch_data['vol_rank'] > 0.7) & (garch_data['vol_rank'].shift(1) <= 0.7)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_garch_vol', index=data.index),
                'signal_strength': (1 - garch_data['vol_rank']).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        garch_data = self.calculate(data, params)
        return pd.DataFrame({
            'garch_vol': garch_data['garch_vol'],
            'vol_forecast': garch_data['vol_forecast'],
            'vol_rank': garch_data['vol_rank'],
            'persistence': garch_data['persistence'],
            'garch_slope': garch_data['garch_vol'].diff(),
            'forecast_error': garch_data['garch_vol'] - garch_data['vol_forecast']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
