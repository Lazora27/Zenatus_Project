"""293 - Monte Carlo Simulation"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MonteCarlo:
    """Monte Carlo Simulation - Probabilistic Price Paths"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30], 'optimize': True},
        'num_simulations': {'default': 100, 'values': [50,100,200], 'optimize': True},
        'forecast_steps': {'default': 5, 'values': [3,5,10], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MonteCarlo", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        num_sims = params.get('num_simulations', 100)
        forecast_steps = params.get('forecast_steps', 5)
        returns = data['close'].pct_change()
        
        # Rolling statistics
        mean_return = returns.rolling(period).mean()
        std_return = returns.rolling(period).std()
        
        # Monte Carlo forecast
        mc_mean = pd.Series(0.0, index=data.index)
        mc_std = pd.Series(0.0, index=data.index)
        mc_upper = pd.Series(0.0, index=data.index)
        mc_lower = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            if pd.notna(mean_return.iloc[i]) and pd.notna(std_return.iloc[i]):
                # Simulate future paths
                current_price = data['close'].iloc[i]
                simulated_prices = []
                
                for _ in range(num_sims):
                    price = current_price
                    for _ in range(forecast_steps):
                        random_return = np.random.normal(mean_return.iloc[i], std_return.iloc[i])
                        price *= (1 + random_return)
                    simulated_prices.append(price)
                
                mc_mean.iloc[i] = np.mean(simulated_prices)
                mc_std.iloc[i] = np.std(simulated_prices)
                mc_upper.iloc[i] = np.percentile(simulated_prices, 95)
                mc_lower.iloc[i] = np.percentile(simulated_prices, 5)
        
        # Probability of upward move
        prob_up = (mc_mean > data['close']).astype(float)
        
        # Confidence interval width
        ci_width = (mc_upper - mc_lower) / data['close']
        
        return pd.DataFrame({
            'mc_mean': mc_mean,
            'mc_std': mc_std,
            'mc_upper': mc_upper,
            'mc_lower': mc_lower,
            'prob_up': prob_up,
            'ci_width': ci_width
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        mc_data = self.calculate(data, params)
        entries = (mc_data['prob_up'] > 0.6) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': mc_data['prob_up']}
    
    def generate_signals_dynamic(self, data, params):
        mc_data = self.calculate(data, params)
        entries = (mc_data['prob_up'] > 0.6) & (data['close'] > data['close'].shift(1))
        exits = (mc_data['prob_up'] < 0.4)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('low_prob_up', index=data.index),
                'signal_strength': mc_data['prob_up']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
