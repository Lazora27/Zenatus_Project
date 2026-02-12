"""032 - Vortex Indicator"""
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

class Indicator_Vortex:
    """Vortex Indicator - Trend Strength"""
    PARAMETERS = {
        'period': {'default': 14, 'min': 2, 'max': 50, 'values': [7,8,11,13,14,17,19,21,23], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Vortex", "Trend", __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Berechnet Vortex Indicator."""
        period = params.get('period', 14)
        high, low, close = data['high'], data['low'], data['close']
        
        # Vortex Movement
        vm_plus = abs(high - low.shift(1))
        vm_minus = abs(low - high.shift(1))
        
        # True Range
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        
        # Vortex Indicator
        vi_plus = vm_plus.rolling(period).sum() / tr.rolling(period).sum()
        vi_minus = vm_minus.rolling(period).sum() / tr.rolling(period).sum()
        
        return pd.DataFrame({'vi_plus': vi_plus, 'vi_minus': vi_minus}, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        result = self.calculate(data, params)
        entries = (result['vi_plus'] > result['vi_minus']) & (result['vi_plus'].shift(1) <= result['vi_minus'].shift(1))
        
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
        
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels,
                'signal_strength': abs(result['vi_plus'] - result['vi_minus'])}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        result = self.calculate(data, params)
        entries = (result['vi_plus'] > result['vi_minus']) & (result['vi_plus'].shift(1) <= result['vi_minus'].shift(1))
        exits = (result['vi_minus'] > result['vi_plus']) & (result['vi_minus'].shift(1) <= result['vi_plus'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('vortex_cross', index=data.index),
                'signal_strength': abs(result['vi_plus'] - result['vi_minus'])}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['vi_plus'], features['vi_minus'] = result['vi_plus'], result['vi_minus']
        features['vi_diff'] = result['vi_plus'] - result['vi_minus']
        return features
    
    def validate_params(self, params: Dict): pass
    def get_parameter_grid(self) -> Dict: return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'],
                                         tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
