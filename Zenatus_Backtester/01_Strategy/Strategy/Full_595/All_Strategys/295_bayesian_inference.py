"""295 - Bayesian Inference"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BayesianInference:
    """Bayesian Inference - Probabilistic Belief Update"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'prior_prob': {'default': 0.5, 'values': [0.3,0.5,0.7], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BayesianInference", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        prior_prob = params.get('prior_prob', 0.5)
        close = data['close']
        
        # Up/Down moves
        up_move = (close > close.shift(1)).astype(int)
        
        # Rolling probability of up move (likelihood)
        likelihood_up = up_move.rolling(period).mean()
        
        # Bayesian update: P(Up|Data) = P(Data|Up) * P(Up) / P(Data)
        # Simplified: posterior = likelihood * prior / normalizer
        posterior_up = pd.Series(prior_prob, index=close.index)
        
        for i in range(period, len(close)):
            if pd.notna(likelihood_up.iloc[i]):
                # Update belief based on evidence
                likelihood = likelihood_up.iloc[i]
                prior = posterior_up.iloc[i-1]
                
                # Bayes' theorem (simplified)
                posterior = (likelihood * prior) / ((likelihood * prior) + ((1 - likelihood) * (1 - prior)) + 1e-10)
                posterior_up.iloc[i] = posterior
        
        # Confidence in direction
        confidence = abs(posterior_up - 0.5) * 2  # Scale to 0-1
        
        # Strong belief
        strong_bullish = (posterior_up > 0.7).astype(int)
        strong_bearish = (posterior_up < 0.3).astype(int)
        
        # Belief change
        belief_change = posterior_up.diff()
        
        return pd.DataFrame({
            'likelihood_up': likelihood_up,
            'posterior_up': posterior_up,
            'confidence': confidence,
            'strong_bullish': strong_bullish,
            'strong_bearish': strong_bearish,
            'belief_change': belief_change
        }, index=data.index).fillna(0.5)
    
    def generate_signals_fixed(self, data, params):
        bayes_data = self.calculate(data, params)
        entries = (bayes_data['strong_bullish'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': bayes_data['confidence']}
    
    def generate_signals_dynamic(self, data, params):
        bayes_data = self.calculate(data, params)
        entries = (bayes_data['strong_bullish'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (bayes_data['strong_bearish'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('strong_bearish', index=data.index),
                'signal_strength': bayes_data['confidence']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
