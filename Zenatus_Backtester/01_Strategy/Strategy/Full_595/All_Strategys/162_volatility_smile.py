"""162 - Volatility Smile"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolatilitySmile:
    """Volatility Smile - Vol by Price Distance (Moneyness)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'price_levels': {'default': 5, 'values': [3,5,7], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolatilitySmile", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        price_levels = params.get('price_levels', 5)
        
        close = data['close']
        log_returns = np.log(close / close.shift(1))
        
        # Base volatility
        base_vol = log_returns.rolling(period).std() * np.sqrt(252) * 100
        
        # Calculate vol for different price levels (moneyness)
        # ATM (at-the-money): current price
        atm_vol = base_vol
        
        # OTM/ITM: price +/- 1%, 2%, 3%
        price_ma = close.rolling(period).mean()
        moneyness = (close - price_ma) / price_ma * 100
        
        # Vol smile: higher vol at extremes
        smile_factor = 1 + abs(moneyness) / 10
        smile_vol = base_vol * smile_factor
        
        # Smile skew (asymmetry)
        left_vol = base_vol * (1 + abs(moneyness.clip(upper=0)) / 10)
        right_vol = base_vol * (1 + abs(moneyness.clip(lower=0)) / 10)
        smile_skew = right_vol - left_vol
        
        # Smile curvature
        smile_curve = smile_vol - atm_vol
        
        return pd.DataFrame({
            'atm_vol': atm_vol,
            'smile_vol': smile_vol,
            'smile_skew': smile_skew,
            'smile_curve': smile_curve,
            'moneyness': moneyness
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        smile_data = self.calculate(data, params)
        # Entry when smile is flat (low skew) - stable market
        entries = (abs(smile_data['smile_skew']) < smile_data['smile_skew'].rolling(50).quantile(0.3))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': (1 / (abs(smile_data['smile_skew']) + 1)).clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        smile_data = self.calculate(data, params)
        entries = (abs(smile_data['smile_skew']) < smile_data['smile_skew'].rolling(50).quantile(0.3))
        exits = (abs(smile_data['smile_skew']) > smile_data['smile_skew'].rolling(50).quantile(0.7))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_smile_skew', index=data.index),
                'signal_strength': (1 / (abs(smile_data['smile_skew']) + 1)).clip(0, 1)}
    
    def get_ml_features(self, data, params):
        smile_data = self.calculate(data, params)
        return pd.DataFrame({
            'smile_skew': smile_data['smile_skew'],
            'smile_curve': smile_data['smile_curve'],
            'moneyness': smile_data['moneyness'],
            'smile_asymmetry': smile_data['smile_skew'] / (smile_data['atm_vol'] + 1e-10),
            'smile_steep': (abs(smile_data['smile_skew']) > smile_data['smile_skew'].rolling(50).quantile(0.7)).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
