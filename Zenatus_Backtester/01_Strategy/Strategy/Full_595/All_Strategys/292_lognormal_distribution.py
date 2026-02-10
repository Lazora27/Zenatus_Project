"""292 - Log-Normal Distribution"""
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

class Indicator_LogNormalDistribution:
    """Log-Normal Distribution - Price Distribution Analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "LogNormalDistribution", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        close = data['close']
        
        # Log returns (more appropriate for prices)
        log_returns = np.log(close / close.shift(1))
        
        # Rolling parameters
        mu = log_returns.rolling(period).mean()
        sigma = log_returns.rolling(period).std()
        
        # Expected price (geometric mean)
        expected_price = close.shift(1) * np.exp(mu + 0.5 * sigma**2)
        
        # Median price
        median_price = close.shift(1) * np.exp(mu)
        
        # Mode price
        mode_price = close.shift(1) * np.exp(mu - sigma**2)
        
        # Probability that price exceeds current level
        if len(close) > 0:
            prob_exceed = pd.Series(0.5, index=close.index)
            for i in range(period, len(close)):
                if pd.notna(mu.iloc[i]) and pd.notna(sigma.iloc[i]) and sigma.iloc[i] > 0:
                    z = (np.log(close.iloc[i] / close.iloc[i-1]) - mu.iloc[i]) / sigma.iloc[i]
                    prob_exceed.iloc[i] = 1 - stats.norm.cdf(z)
        else:
            prob_exceed = pd.Series(0.5, index=close.index)
        
        # Price deviation from expected
        price_deviation = (close - expected_price) / expected_price
        
        return pd.DataFrame({
            'mu': mu,
            'sigma': sigma,
            'expected_price': expected_price,
            'median_price': median_price,
            'mode_price': mode_price,
            'prob_exceed': prob_exceed,
            'price_deviation': price_deviation
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ln_data = self.calculate(data, params)
        # Buy when price below expected (undervalued)
        entries = (data['close'] < ln_data['expected_price']) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(ln_data['price_deviation']).clip(0, 0.1)*10}
    
    def generate_signals_dynamic(self, data, params):
        ln_data = self.calculate(data, params)
        entries = (data['close'] < ln_data['expected_price']) & (data['close'] > data['close'].shift(1))
        exits = (data['close'] > ln_data['expected_price'])
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('above_expected', index=data.index),
                'signal_strength': abs(ln_data['price_deviation']).clip(0, 0.1)*10}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
