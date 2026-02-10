"""
013 - Variable Index Dynamic Average (VIDYA)
Volatilitäts-adaptiver EMA
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


class Indicator_VIDYA:
    """Variable Index Dynamic Average (VIDYA) - Trend"""
    
    PARAMETERS = {
        'period': {'default': 20, 'min': 2, 'max': 200, 
                   'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
                   'optimize': True, 'ml_feature': True},
        'cmo_period': {'default': 9, 'min': 2, 'max': 50, 
                       'values': [5,7,9,11,13,15,17,19,21], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'min': 20, 'max': 200, 
                    'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'min': 10, 'max': 100, 
                    'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name = "VIDYA"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Berechnet VIDYA mit CMO-basierter Anpassung."""
        self.validate_params(params)
        period = params.get('period', 20)
        cmo_period = params.get('cmo_period', 9)
        
        # Chande Momentum Oscillator
        up = data['close'].diff().clip(lower=0)
        down = -data['close'].diff().clip(upper=0)
        sum_up = up.rolling(cmo_period).sum()
        sum_down = down.rolling(cmo_period).sum()
        cmo = abs((sum_up - sum_down) / (sum_up + sum_down + 1e-10))
        
        # Adaptive Alpha
        base_alpha = 2 / (period + 1)
        adaptive_alpha = base_alpha * cmo
        
        # VIDYA
        vidya = data['close'].ewm(alpha=base_alpha, adjust=False).mean()
        for i in range(1, len(data)):
            alpha = adaptive_alpha.iloc[i] if not np.isnan(adaptive_alpha.iloc[i]) else base_alpha
            vidya.iloc[i] = alpha * data['close'].iloc[i] + (1 - alpha) * vidya.iloc[i-1]
        
        return vidya
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        vidya = self.calculate(data, params)
        entries = (data['close'] > vidya) & (data['close'].shift(1) <= vidya.shift(1))
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
                'signal_strength': abs(data['close'] - vidya) / vidya}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        vidya = self.calculate(data, params)
        entries = (data['close'] > vidya) & (data['close'].shift(1) <= vidya.shift(1))
        exits = (data['close'] < vidya) & (data['close'].shift(1) >= vidya.shift(1))
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'vidya_reverse_cross'
        return {'entries': entries, 'exits': exits, 'exit_reason': exit_reason,
                'signal_strength': abs(data['close'] - vidya) / vidya}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        vidya = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['vidya_value'] = vidya
        features['vidya_slope'] = vidya.diff()
        features['distance_from_price'] = data['close'] - vidya
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
