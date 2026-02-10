"""297 - Hypothesis Testing"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
from scipy import stats
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HypothesisTesting:
    """Hypothesis Testing - Statistical Significance Tests"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'alpha': {'default': 0.05, 'values': [0.01,0.05,0.10], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HypothesisTesting", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        alpha = params.get('alpha', 0.05)
        returns = data['close'].pct_change()
        
        # Rolling t-test (H0: mean return = 0)
        mean = returns.rolling(period).mean()
        std = returns.rolling(period).std()
        n = period
        
        # T-statistic
        t_stat = mean / (std / np.sqrt(n) + 1e-10)
        
        # Critical value
        t_critical = stats.t.ppf(1 - alpha/2, n - 1)
        
        # P-value (two-tailed)
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 1))
        
        # Reject null hypothesis?
        reject_null = (abs(t_stat) > t_critical).astype(int)
        significant = (p_value < alpha).astype(int)
        
        # Direction of significance
        significant_positive = ((t_stat > t_critical) & significant).astype(int)
        significant_negative = ((t_stat < -t_critical) & significant).astype(int)
        
        return pd.DataFrame({
            't_stat': t_stat,
            't_critical': t_critical,
            'p_value': p_value,
            'reject_null': reject_null,
            'significant': significant,
            'significant_positive': significant_positive,
            'significant_negative': significant_negative
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ht_data = self.calculate(data, params)
        entries = (ht_data['significant_positive'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(ht_data['t_stat']).clip(0, 5)/5}
    
    def generate_signals_dynamic(self, data, params):
        ht_data = self.calculate(data, params)
        entries = (ht_data['significant_positive'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (ht_data['significant_negative'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('significant_negative', index=data.index),
                'signal_strength': abs(ht_data['t_stat']).clip(0, 5)/5}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
