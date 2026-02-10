"""256 - Linear Regression"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_LinearRegression:
    """Linear Regression - Trend Line Forecast"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "LinearRegression", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        close = data['close']
        
        def fit_linreg(window):
            if len(window) < 2:
                return np.nan
            X = np.arange(len(window)).reshape(-1, 1)
            y = window.values
            model = LinearRegression()
            model.fit(X, y)
            return model.predict([[len(window)]])[0]
        
        forecast = close.rolling(period).apply(fit_linreg, raw=False)
        
        above_forecast = (close > forecast).astype(int)
        below_forecast = (close < forecast).astype(int)
        forecast_error = close - forecast
        
        return pd.DataFrame({
            'forecast': forecast,
            'above_forecast': above_forecast,
            'below_forecast': below_forecast,
            'forecast_error': forecast_error
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        lr_data = self.calculate(data, params)
        entries = (data['close'] > lr_data['forecast']) & (data['close'].shift(1) <= lr_data['forecast'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(lr_data['forecast_error'] / data['close']).clip(0, 0.1)*10}
    
    def generate_signals_dynamic(self, data, params):
        lr_data = self.calculate(data, params)
        entries = (data['close'] > lr_data['forecast']) & (data['close'].shift(1) <= lr_data['forecast'].shift(1))
        exits = (data['close'] < lr_data['forecast']) & (data['close'].shift(1) >= lr_data['forecast'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_forecast', index=data.index),
                'signal_strength': abs(lr_data['forecast_error'] / data['close']).clip(0, 0.1)*10}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
