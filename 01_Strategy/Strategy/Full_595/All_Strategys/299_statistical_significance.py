"""299 - Statistical Significance"""
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

class Indicator_StatisticalSignificance:
    """Statistical Significance - Multi-Test Significance Analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "StatisticalSignificance", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        returns = data['close'].pct_change()
        
        # Multiple significance tests
        mean = returns.rolling(period).mean()
        std = returns.rolling(period).std()
        
        # T-test significance
        t_stat = mean / (std / np.sqrt(period) + 1e-10)
        t_pvalue = 2 * (1 - stats.t.cdf(abs(t_stat), period - 1))
        t_significant = (t_pvalue < 0.05).astype(int)
        
        # Z-test significance
        zscore = (returns - mean) / (std + 1e-10)
        z_pvalue = 2 * (1 - stats.norm.cdf(abs(zscore)))
        z_significant = (z_pvalue < 0.05).astype(int)
        
        # Combined significance score
        combined_significance = (t_significant + z_significant) / 2
        
        # Effect size (Cohen's d)
        cohens_d = mean / (std + 1e-10)
        
        # Practical significance (large effect)
        practical_significant = (abs(cohens_d) > 0.5).astype(int)
        
        # Overall significance
        overall_significant = ((t_significant == 1) & (z_significant == 1) & (practical_significant == 1)).astype(int)
        
        return pd.DataFrame({
            't_stat': t_stat,
            't_pvalue': t_pvalue,
            't_significant': t_significant,
            'zscore': zscore,
            'z_pvalue': z_pvalue,
            'z_significant': z_significant,
            'cohens_d': cohens_d,
            'practical_significant': practical_significant,
            'combined_significance': combined_significance,
            'overall_significant': overall_significant
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        sig_data = self.calculate(data, params)
        entries = (sig_data['overall_significant'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': sig_data['combined_significance']}
    
    def generate_signals_dynamic(self, data, params):
        sig_data = self.calculate(data, params)
        entries = (sig_data['overall_significant'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (sig_data['combined_significance'] < 0.3)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('low_significance', index=data.index),
                'signal_strength': sig_data['combined_significance']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
