"""
052 - Force Index
Kombiniert Preis und Volumen für Trend-Stärke
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


class Indicator_ForceIndex:
    """Force Index - Volume Momentum"""
    
    PARAMETERS = {
        'period': {'default': 13, 'min': 2, 'max': 50, 'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ForceIndex", "Volume", __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Force Index = (Close - Close[prev]) * Volume, dann EMA"""
        self.validate_params(params)
        period = params.get('period', 13)
        raw_force = (data['close'] - data['close'].shift(1)) * data['volume']
        return raw_force.ewm(span=period, adjust=False).mean().fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        fi = self.calculate(data, params)
        entries = (fi > 0) & (fi.shift(1) <= 0)
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_position, entry_price, tp_level, sl_level = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position, entry_price = True, data['close'].iloc[i]
                tp_level, sl_level = entry_price + (tp_pips * pip), entry_price - (sl_pips * pip)
            elif in_position and (data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level):
                exits.iloc[i], in_position = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index), 
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(fi).clip(0, 100000) / 100000}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        fi = self.calculate(data, params)
        entries, exits = (fi > 0) & (fi.shift(1) <= 0), (fi < 0) & (fi.shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('force_reverse', index=data.index),
                'signal_strength': abs(fi).clip(0, 100000) / 100000}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        fi = self.calculate(data, params)
        return pd.DataFrame({'fi_value': fi, 'fi_slope': fi.diff(), 'fi_positive': (fi > 0).astype(int)}, index=data.index)
    
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
