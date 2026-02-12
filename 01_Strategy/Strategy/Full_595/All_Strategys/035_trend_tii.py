"""035 - Trend Intensity Index (TII)"""
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

class Indicator_TII:
    """Trend Intensity Index - Trend Strength"""
    PARAMETERS = {
        'period': {'default': 30, 'min': 10, 'max': 60, 'values': [20,25,30,35,40,45,50], 'optimize': True, 'ml_feature': True},
        'threshold': {'default': 50, 'min': 30, 'max': 70, 'values': [40,45,50,55,60], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TII", "Trend", __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Berechnet Trend Intensity Index."""
        period = params.get('period', 30)
        close = data['close']
        
        # Simple Moving Average
        sma = close.rolling(period).mean()
        
        # Count bars above/below SMA
        above_sma = (close > sma).rolling(period).sum()
        
        # TII = (above_sma / period) * 100
        tii = (above_sma / period) * 100
        
        return tii
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        tii = self.calculate(data, params)
        threshold = params.get('threshold', 50)
        
        entries = (tii > threshold) & (tii.shift(1) <= threshold)
        
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
                'signal_strength': tii / 100}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        tii = self.calculate(data, params)
        threshold = params.get('threshold', 50)
        
        entries = (tii > threshold) & (tii.shift(1) <= threshold)
        exits = (tii < (100 - threshold)) & (tii.shift(1) >= (100 - threshold))
        
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('tii_reverse', index=data.index),
                'signal_strength': tii / 100}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        tii = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['tii_value'] = tii
        features['tii_slope'] = tii.diff()
        features['tii_normalized'] = (tii - 50) / 50
        return features
    
    def validate_params(self, params: Dict): pass
    def get_parameter_grid(self) -> Dict: return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'],
                                         tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
