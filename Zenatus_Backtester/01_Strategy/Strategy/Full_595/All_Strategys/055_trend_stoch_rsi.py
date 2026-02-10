"""055 - Stochastic RSI"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_StochRSI:
    """Stochastic RSI - RSI mit Stochastic"""
    PARAMETERS = {
        'rsi_period': {'default': 14, 'min': 5, 'max': 50, 'values': [5,7,8,11,13,14,17,19,21,23,29,31,34,37,41,43,47], 'optimize': True, 'ml_feature': True},
        'stoch_period': {'default': 14, 'min': 3, 'max': 30, 'values': [3,5,7,8,11,13,14,17,19,21,23,29], 'optimize': True, 'ml_feature': True},
        'smooth_k': {'default': 3, 'min': 1, 'max': 10, 'values': [1,2,3,4,5,6,7,8,9,10], 'optimize': True},
        'smooth_d': {'default': 3, 'min': 1, 'max': 10, 'values': [1,2,3,4,5,6,7,8,9,10], 'optimize': True},
        'overbought': {'default': 80, 'values': [70,75,80,85,90], 'optimize': True},
        'oversold': {'default': 20, 'values': [10,15,20,25,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    def __init__(self):
        self.name, self.category, self.version = "StochRSI", "Momentum", __version__
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        self.validate_params(params)
        rsi_period, stoch_period = params.get('rsi_period', 14), params.get('stoch_period', 14)
        smooth_k, smooth_d = params.get('smooth_k', 3), params.get('smooth_d', 3)
        delta = data['close'].diff()
        gain, loss = delta.where(delta > 0, 0), -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/rsi_period, min_periods=rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/rsi_period, min_periods=rsi_period, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        rsi_min = rsi.rolling(window=stoch_period, min_periods=1).min()
        rsi_max = rsi.rolling(window=stoch_period, min_periods=1).max()
        stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min + 1e-10)) * 100
        k = stoch_rsi.rolling(window=smooth_k, min_periods=1).mean()
        d = k.rolling(window=smooth_d, min_periods=1).mean()
        return pd.DataFrame({'k': k.fillna(50), 'd': d.fillna(50)}, index=data.index)
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        result = self.calculate(data, params)
        k, d, oversold = result['k'], result['d'], params.get('oversold', 20)
        entries = (k > d) & (k.shift(1) <= d.shift(1)) & (k < oversold)
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_position, entry_price, tp_level, sl_level = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position, entry_price = True, data['close'].iloc[i]
                tp_level, sl_level = entry_price + (tp_pips * pip), entry_price - (sl_pips * pip)
            elif in_position and (data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level):
                exits.iloc[i], in_position = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index), 
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(k - d) / 100}
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        result = self.calculate(data, params)
        k, d = result['k'], result['d']
        oversold, overbought = params.get('oversold', 20), params.get('overbought', 80)
        entries = (k > d) & (k.shift(1) <= d.shift(1)) & (k < oversold)
        exits = (k < d) & (k.shift(1) >= d.shift(1)) & (k > overbought)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('stochrsi_overbought', index=data.index), 'signal_strength': abs(k - d) / 100}
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        result = self.calculate(data, params)
        k, d = result['k'], result['d']
        return pd.DataFrame({'stochrsi_k': k, 'stochrsi_d': d, 'stochrsi_divergence': k - d,
                            'stochrsi_overbought': (k > params.get('overbought', 80)).astype(int),
                            'stochrsi_oversold': (k < params.get('oversold', 20)).astype(int)}, index=data.index)
    def validate_params(self, params: Dict) -> None:
        for k, v in params.items():
            if k in self.PARAMETERS and ('min' in self.PARAMETERS[k] and v < self.PARAMETERS[k]['min'] or 'max' in self.PARAMETERS[k] and v > self.PARAMETERS[k]['max']):
                raise ValueError(f"{k} out of range")
    def get_parameter_grid(self) -> Dict:
        return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0) -> vbt.Portfolio:
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'],
                                         tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
