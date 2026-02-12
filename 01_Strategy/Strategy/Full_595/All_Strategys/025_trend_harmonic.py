"""025 - Harmonic Moving Average"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_Harmonic:
    """Harmonic Moving Average - Trend"""
    PARAMETERS = {
        'period': {'default': 20, 'min': 2, 'max': 200, 'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    def __init__(self):
        self.name, self.category, self.version = "Harmonic", "Trend", "1.0.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        period = params.get('period', 20)
        # HMA = n / (1/P1 + 1/P2 + ... + 1/Pn)
        reciprocal = 1 / (data['close'].replace(0, np.nan))
        harmonic = period / reciprocal.rolling(window=period).sum()
        return harmonic
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict:
        harmonic = self.calculate(data, params)
        entries = (data['close'] > harmonic) & (data['close'].shift(1) <= harmonic.shift(1))
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        # TP/SL nur bei Entry setzen, NICHT forward-fillen!
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
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': abs(data['close'] - harmonic) / harmonic}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict:
        harmonic = self.calculate(data, params)
        entries = (data['close'] > harmonic) & (data['close'].shift(1) <= harmonic.shift(1))
        exits = (data['close'] < harmonic) & (data['close'].shift(1) >= harmonic.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('harmonic_cross', index=data.index), 'signal_strength': abs(data['close'] - harmonic) / harmonic}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        harmonic = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['harmonic_value'], features['harmonic_slope'] = harmonic, harmonic.diff()
        features['distance_from_price'] = data['close'] - harmonic
        return features
    
    def validate_params(self, params: Dict): pass
    def get_parameter_grid(self) -> Dict: return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
