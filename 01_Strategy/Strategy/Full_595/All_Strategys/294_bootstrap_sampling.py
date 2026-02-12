"""294 - Bootstrap Sampling"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BootstrapSampling:
    """Bootstrap Sampling - Resampling-Based Confidence Intervals"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'num_bootstrap': {'default': 100, 'values': [50,100,200], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BootstrapSampling", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        num_bootstrap = params.get('num_bootstrap', 100)
        returns = data['close'].pct_change()
        
        # Bootstrap mean and confidence intervals
        bootstrap_mean = pd.Series(0.0, index=data.index)
        bootstrap_std = pd.Series(0.0, index=data.index)
        bootstrap_lower = pd.Series(0.0, index=data.index)
        bootstrap_upper = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = returns.iloc[i-period:i].dropna()
            if len(window) > 0:
                bootstrap_means = []
                for _ in range(num_bootstrap):
                    sample = np.random.choice(window.values, size=len(window), replace=True)
                    bootstrap_means.append(np.mean(sample))
                
                bootstrap_mean.iloc[i] = np.mean(bootstrap_means)
                bootstrap_std.iloc[i] = np.std(bootstrap_means)
                bootstrap_lower.iloc[i] = np.percentile(bootstrap_means, 5)
                bootstrap_upper.iloc[i] = np.percentile(bootstrap_means, 95)
        
        # Confidence in positive returns
        confidence_positive = (bootstrap_lower > 0).astype(int)
        
        # Bootstrap signal strength
        signal_strength = abs(bootstrap_mean) / (bootstrap_std + 1e-10)
        
        return pd.DataFrame({
            'bootstrap_mean': bootstrap_mean,
            'bootstrap_std': bootstrap_std,
            'bootstrap_lower': bootstrap_lower,
            'bootstrap_upper': bootstrap_upper,
            'confidence_positive': confidence_positive,
            'signal_strength': signal_strength
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        bs_data = self.calculate(data, params)
        entries = (bs_data['confidence_positive'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': bs_data['signal_strength'].clip(0, 5)/5}
    
    def generate_signals_dynamic(self, data, params):
        bs_data = self.calculate(data, params)
        entries = (bs_data['confidence_positive'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (bs_data['bootstrap_upper'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('negative_confidence', index=data.index),
                'signal_strength': bs_data['signal_strength'].clip(0, 5)/5}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
