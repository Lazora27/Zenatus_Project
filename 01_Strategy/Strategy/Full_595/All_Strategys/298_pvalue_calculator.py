"""298 - P-Value Calculator"""
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

class Indicator_PValueCalculator:
    """P-Value Calculator - Statistical Significance Measurement"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PValueCalculator", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        returns = data['close'].pct_change()
        
        # Rolling statistics
        mean = returns.rolling(period).mean()
        std = returns.rolling(period).std()
        
        # Z-score
        zscore = (returns - mean) / (std + 1e-10)
        
        # P-value (two-tailed)
        pvalue = 2 * (1 - stats.norm.cdf(abs(zscore)))
        
        # Significance levels
        very_significant = (pvalue < 0.01).astype(int)  # 99% confidence
        significant = (pvalue < 0.05).astype(int)  # 95% confidence
        marginally_significant = (pvalue < 0.10).astype(int)  # 90% confidence
        
        # Log p-value (for better visualization)
        log_pvalue = -np.log10(pvalue + 1e-10)
        
        # Signal strength (inverse of p-value)
        signal_strength = 1 - pvalue
        
        return pd.DataFrame({
            'zscore': zscore,
            'pvalue': pvalue,
            'log_pvalue': log_pvalue,
            'very_significant': very_significant,
            'significant': significant,
            'marginally_significant': marginally_significant,
            'signal_strength': signal_strength
        }, index=data.index).fillna(0.5)
    
    def generate_signals_fixed(self, data, params):
        pv_data = self.calculate(data, params)
        # Trade on significant moves
        entries = (pv_data['significant'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': pv_data['signal_strength']}
    
    def generate_signals_dynamic(self, data, params):
        pv_data = self.calculate(data, params)
        entries = (pv_data['significant'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (pv_data['pvalue'] > 0.5)  # Exit when not significant
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('not_significant', index=data.index),
                'signal_strength': pv_data['signal_strength']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
