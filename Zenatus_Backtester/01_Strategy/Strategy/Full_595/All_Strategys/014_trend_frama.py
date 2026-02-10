"""
014 - Fractal Adaptive Moving Average (FRAMA)
Fraktal-Dimensions-adaptiver MA
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


class Indicator_FRAMA:
    """Fractal Adaptive Moving Average (FRAMA) - Trend"""
    
    PARAMETERS = {
        'period': {'default': 20, 'min': 4, 'max': 200,
                   'values': [8,12,16,20,24,28,32,36,40,44,48,52,56,60],
                   'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'min': 20, 'max': 200,
                    'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'min': 10, 'max': 100,
                    'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name = "FRAMA"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Berechnet FRAMA mit Fraktal-Dimension."""
        self.validate_params(params)
        period = params.get('period', 20)
        n = period // 2
        
        high, low, close = data['high'], data['low'], data['close']
        
        # Fraktal Dimension
        n1_high = high.rolling(n).max()
        n1_low = low.rolling(n).min()
        n2_high = high.rolling(n).max().shift(n)
        n2_low = low.rolling(n).min().shift(n)
        n3_high = high.rolling(period).max()
        n3_low = low.rolling(period).min()
        
        d = (np.log(n1_high - n1_low + n2_high - n2_low) - np.log(n3_high - n3_low)) / np.log(2)
        d = d.clip(-0.5, 0.5)
        
        # Alpha
        alpha = np.exp(-4.6 * (d + 1))
        alpha = alpha.clip(0.01, 1)
        
        # FRAMA
        frama = pd.Series(np.nan, index=close.index)
        frama.iloc[period] = close.iloc[period]
        for i in range(period + 1, len(close)):
            a = alpha.iloc[i] if not np.isnan(alpha.iloc[i]) else 0.5
            frama.iloc[i] = a * close.iloc[i] + (1 - a) * frama.iloc[i-1]
        
        return frama
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        frama = self.calculate(data, params)
        entries = (data['close'] > frama) & (data['close'].shift(1) <= frama.shift(1))
        tp_pips, sl_pips = params.get('tp_pips', 50), params.get('sl_pips', 25)
        pip = 0.0001
        
        # Manuelle TP/SL Exit-Logik
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
                'signal_strength': abs(data['close'] - frama) / frama}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        frama = self.calculate(data, params)
        entries = (data['close'] > frama) & (data['close'].shift(1) <= frama.shift(1))
        exits = (data['close'] < frama) & (data['close'].shift(1) >= frama.shift(1))
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'frama_reverse_cross'
        return {'entries': entries, 'exits': exits, 'exit_reason': exit_reason,
                'signal_strength': abs(data['close'] - frama) / frama}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        frama = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['frama_value'] = frama
        features['frama_slope'] = frama.diff()
        features['distance_from_price'] = data['close'] - frama
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
