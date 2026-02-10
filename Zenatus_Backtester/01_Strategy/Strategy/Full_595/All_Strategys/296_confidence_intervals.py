"""296 - Confidence Intervals"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
from scipy import stats
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ConfidenceIntervals:
    """Confidence Intervals - Statistical Range Estimation"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'confidence_level': {'default': 0.95, 'values': [0.90,0.95,0.99], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ConfidenceIntervals", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        confidence_level = params.get('confidence_level', 0.95)
        returns = data['close'].pct_change()
        
        # Rolling statistics
        mean = returns.rolling(period).mean()
        std = returns.rolling(period).std()
        n = period
        
        # Critical value for confidence level
        alpha = 1 - confidence_level
        z_critical = stats.norm.ppf(1 - alpha/2)
        
        # Confidence interval for mean
        margin_of_error = z_critical * std / np.sqrt(n)
        ci_lower = mean - margin_of_error
        ci_upper = mean + margin_of_error
        
        # CI width
        ci_width = ci_upper - ci_lower
        
        # Price confidence intervals
        current_price = data['close']
        price_ci_lower = current_price * (1 + ci_lower)
        price_ci_upper = current_price * (1 + ci_upper)
        
        # Is current return within CI?
        within_ci = ((returns >= ci_lower) & (returns <= ci_upper)).astype(int)
        
        # Breakout signals
        breakout_upper = (returns > ci_upper).astype(int)
        breakout_lower = (returns < ci_lower).astype(int)
        
        return pd.DataFrame({
            'mean': mean,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'ci_width': ci_width,
            'price_ci_lower': price_ci_lower,
            'price_ci_upper': price_ci_upper,
            'within_ci': within_ci,
            'breakout_upper': breakout_upper,
            'breakout_lower': breakout_lower
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ci_data = self.calculate(data, params)
        # Buy on lower breakout (mean reversion)
        entries = (ci_data['breakout_lower'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 / (ci_data['ci_width'] + 1)).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        ci_data = self.calculate(data, params)
        entries = (ci_data['breakout_lower'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (ci_data['breakout_upper'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('upper_breakout', index=data.index),
                'signal_strength': (1 / (ci_data['ci_width'] + 1)).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
