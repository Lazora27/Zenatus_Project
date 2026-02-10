"""
018 - Time Series Forecast (TSF)
Linear Regression Forecast
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__date__ = "2025-10-02"
__status__ = "Production"


class Indicator_TSF:
    """Time Series Forecast (TSF) - Trend"""
    
    PARAMETERS = {
        'period': {'default': 20, 'min': 2, 'max': 200,
                   'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
                   'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'min': 20, 'max': 200,
                    'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'min': 10, 'max': 100,
                    'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name = "TSF"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Berechnet Time Series Forecast."""
        self.validate_params(params)
        period = params.get('period', 20)
        
        def tsf_calc(x):
            if len(x) < period:
                return np.nan
            # Linear Regression
            y = x[-period:]
            X = np.arange(len(y))
            # Least Squares
            slope = (len(y) * np.sum(X * y) - np.sum(X) * np.sum(y)) / (len(y) * np.sum(X**2) - np.sum(X)**2)
            intercept = (np.sum(y) - slope * np.sum(X)) / len(y)
            # Forecast next value
            forecast = slope * len(y) + intercept
            return forecast
        
        tsf = data['close'].rolling(window=period).apply(tsf_calc, raw=True)
        return tsf
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        tsf = self.calculate(data, params)
        entries = (data['close'] > tsf) & (data['close'].shift(1) <= tsf.shift(1))
        tp_pips, sl_pips = params.get('tp_pips', 50), params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price, tp_level, sl_level = 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        return {'entries': entries, 'exits': exits,
                'tp_levels': tp_levels, 'sl_levels': sl_levels,
                'signal_strength': abs(data['close'] - tsf) / tsf}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        tsf = self.calculate(data, params)
        entries = (data['close'] > tsf) & (data['close'].shift(1) <= tsf.shift(1))
        exits = (data['close'] < tsf) & (data['close'].shift(1) >= tsf.shift(1))
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'tsf_reverse_cross'
        return {'entries': entries, 'exits': exits, 'exit_reason': exit_reason,
                'signal_strength': abs(data['close'] - tsf) / tsf}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        tsf = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['tsf_value'] = tsf
        features['tsf_slope'] = tsf.diff()
        features['distance_from_price'] = data['close'] - tsf
        features['forecast_error'] = data['close'] - tsf
        return features
    
    def validate_params(self, params: Dict) -> None:
        for k, v in self.PARAMETERS.items():
            if k in params and ('min' in v and params[k] < v['min'] or 'max' in v and params[k] > v['max']):
                raise ValueError(f"{k} out of range")
    
    def get_parameter_grid(self) -> Dict:
        return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed',
                         init_cash: float = 10000, fees: float = 0.0) -> vbt.Portfolio:
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'],
                                         tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
