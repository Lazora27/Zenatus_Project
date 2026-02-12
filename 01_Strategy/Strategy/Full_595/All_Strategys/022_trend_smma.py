"""022 - Smoothed Moving Average (SMMA)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_SMMA:
    """Smoothed Moving Average (SMMA/RMA) - Trend"""
    PARAMETERS = {
        'period': {'default': 20, 'min': 2, 'max': 200, 'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    def __init__(self):
        self.name, self.category, self.version = "SMMA", "Trend", "1.0.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        period = params.get('period', 20)
        close = data['close']
        smma = pd.Series(np.nan, index=close.index)
        smma.iloc[period-1] = close.iloc[:period].mean()
        for i in range(period, len(close)):
            smma.iloc[i] = (smma.iloc[i-1] * (period - 1) + close.iloc[i]) / period
        return smma
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict:
        smma = self.calculate(data, params)
        entries = (data['close'] > smma) & (data['close'].shift(1) <= smma.shift(1))
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
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': abs(data['close'] - smma) / smma}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict:
        smma = self.calculate(data, params)
        entries = (data['close'] > smma) & (data['close'].shift(1) <= smma.shift(1))
        exits = (data['close'] < smma) & (data['close'].shift(1) >= smma.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('smma_cross', index=data.index), 'signal_strength': abs(data['close'] - smma) / smma}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        smma = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['smma_value'], features['smma_slope'] = smma, smma.diff()
        features['distance_from_price'] = data['close'] - smma
        return features
    
    def validate_params(self, params: Dict): pass
    def get_parameter_grid(self) -> Dict: return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
