"""272 - Holt-Winters"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HoltWinters:
    """Holt-Winters - Triple Exponential Smoothing"""
    PARAMETERS = {
        'alpha': {'default': 0.3, 'values': [0.1,0.2,0.3,0.4], 'optimize': True},
        'beta': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': True},
        'gamma': {'default': 0.1, 'values': [0.05,0.1,0.15,0.2], 'optimize': True},
        'seasonal_period': {'default': 24, 'values': [12,24,48], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HoltWinters", "Statistics", __version__
    
    def calculate(self, data, params):
        alpha = params.get('alpha', 0.3)
        beta = params.get('beta', 0.1)
        gamma = params.get('gamma', 0.1)
        seasonal_period = params.get('seasonal_period', 24)
        close = data['close']
        
        # Simplified Holt-Winters
        # Level component
        level = close.ewm(alpha=alpha, adjust=False).mean()
        
        # Trend component
        trend = level.diff().ewm(alpha=beta, adjust=False).mean()
        
        # Seasonal component
        seasonal = (close - level).rolling(seasonal_period).mean()
        seasonal = seasonal.ewm(alpha=gamma, adjust=False).mean()
        
        # Forecast
        forecast = level + trend + seasonal
        
        above_forecast = (close > forecast).astype(int)
        forecast_error = close - forecast
        
        return pd.DataFrame({
            'level': level,
            'trend': trend,
            'seasonal': seasonal,
            'forecast': forecast,
            'above_forecast': above_forecast,
            'forecast_error': forecast_error
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        hw_data = self.calculate(data, params)
        entries = (data['close'] > hw_data['forecast']) & (data['close'].shift(1) <= hw_data['forecast'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(hw_data['forecast_error'] / data['close']).clip(0, 0.1)*10}
    
    def generate_signals_dynamic(self, data, params):
        hw_data = self.calculate(data, params)
        entries = (data['close'] > hw_data['forecast']) & (data['close'].shift(1) <= hw_data['forecast'].shift(1))
        exits = (data['close'] < hw_data['forecast']) & (data['close'].shift(1) >= hw_data['forecast'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_forecast', index=data.index),
                'signal_strength': abs(hw_data['forecast_error'] / data['close']).clip(0, 0.1)*10}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
