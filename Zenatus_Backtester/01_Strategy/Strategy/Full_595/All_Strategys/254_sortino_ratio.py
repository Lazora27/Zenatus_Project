"""254 - Sortino Ratio"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SortinoRatio:
    """Sortino Ratio - Downside Risk-Adjusted Return"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SortinoRatio", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        returns = data['close'].pct_change()
        
        # Rolling Sortino Ratio
        mean_return = returns.rolling(period).mean()
        
        # Downside deviation (only negative returns)
        downside_returns = returns.copy()
        downside_returns[downside_returns > 0] = 0
        downside_std = downside_returns.rolling(period).std()
        
        sortino = (mean_return / (downside_std + 1e-10)) * np.sqrt(252)  # Annualized
        
        high_sortino = (sortino > 1.5).astype(int)
        negative_sortino = (sortino < 0).astype(int)
        excellent_sortino = (sortino > 3).astype(int)
        
        return pd.DataFrame({
            'sortino': sortino,
            'high_sortino': high_sortino,
            'negative_sortino': negative_sortino,
            'excellent_sortino': excellent_sortino
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        sortino_data = self.calculate(data, params)
        entries = (sortino_data['high_sortino'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': sortino_data['sortino'].clip(-2, 4)/4}
    
    def generate_signals_dynamic(self, data, params):
        sortino_data = self.calculate(data, params)
        entries = (sortino_data['high_sortino'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (sortino_data['negative_sortino'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('negative_sortino', index=data.index),
                'signal_strength': sortino_data['sortino'].clip(-2, 4)/4}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
