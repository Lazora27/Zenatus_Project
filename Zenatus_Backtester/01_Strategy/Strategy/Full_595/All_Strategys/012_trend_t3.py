"""
012 - Tillson T3 Moving Average
Mehrfach geglätteter EMA mit Volume Factor
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


class Indicator_T3:
    """
    Tillson T3 Moving Average - Trend
    
    Beschreibung:
        6-fach geglätteter EMA mit Volume Factor.
        Sehr glatt, minimaler Lag durch spezielle Gewichtung.
    
    Formula:
        T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3
        wobei e1-e6 = aufeinanderfolgende EMAs
        c1-c4 = Koeffizienten basierend auf Volume Factor
    
    Parameters:
        - period: Lookback-Periode (2-200)
        - vfactor: Volume Factor (0.0-1.0, default 0.7)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    """
    
    PARAMETERS = {
        'period': {
            'default': 20,
            'min': 2,
            'max': 200,
            'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'step': 1,
            'optimize': True,
            'ml_feature': True
        },
        'vfactor': {
            'default': 0.7,
            'min': 0.0,
            'max': 1.0,
            'values': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            'step': 0.1,
            'optimize': True,
            'ml_feature': True
        },
        'tp_pips': {
            'default': 50,
            'min': 20,
            'max': 200,
            'values': [30, 40, 50, 60, 75, 100, 125, 150, 200],
            'step': 10,
            'optimize': True,
            'ml_feature': False
        },
        'sl_pips': {
            'default': 25,
            'min': 10,
            'max': 100,
            'values': [10, 15, 20, 25, 30, 40, 50],
            'step': 5,
            'optimize': True,
            'ml_feature': False
        }
    }
    
    def __init__(self):
        self.name = "T3"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Berechnet Tillson T3."""
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        vfactor = params.get('vfactor', self.PARAMETERS['vfactor']['default'])
        
        # Koeffizienten basierend auf Volume Factor
        a = vfactor
        c1 = -a**3
        c2 = 3*a**2 + 3*a**3
        c3 = -6*a**2 - 3*a - 3*a**3
        c4 = 1 + 3*a + a**3 + 3*a**2
        
        # 6-fache EMA
        e1 = data['close'].ewm(span=period, adjust=False).mean()
        e2 = e1.ewm(span=period, adjust=False).mean()
        e3 = e2.ewm(span=period, adjust=False).mean()
        e4 = e3.ewm(span=period, adjust=False).mean()
        e5 = e4.ewm(span=period, adjust=False).mean()
        e6 = e5.ewm(span=period, adjust=False).mean()
        
        # T3 Berechnung
        t3 = c1*e6 + c2*e5 + c3*e4 + c4*e3
        
        return t3
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategie."""
        t3 = self.calculate(data, params)
        entries = (data['close'] > t3) & (data['close'].shift(1) <= t3.shift(1))
        
        tp_pips = params.get('tp_pips', self.PARAMETERS['tp_pips']['default'])
        sl_pips = params.get('sl_pips', self.PARAMETERS['sl_pips']['default'])
        pip = 0.0001
        
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
        signal_strength = abs(data['close'] - t3) / t3
        signal_strength = signal_strength.clip(0, 1)
        
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels,
                'sl_levels': sl_levels, 'signal_strength': signal_strength}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic Exit Strategie."""
        t3 = self.calculate(data, params)
        entries = (data['close'] > t3) & (data['close'].shift(1) <= t3.shift(1))
        exits = (data['close'] < t3) & (data['close'].shift(1) >= t3.shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 't3_reverse_cross'
        
        signal_strength = abs(data['close'] - t3) / t3
        signal_strength = signal_strength.clip(0, 1)
        
        return {'entries': entries, 'exits': exits, 'exit_reason': exit_reason,
                'signal_strength': signal_strength}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extrahiert ML-Features."""
        t3 = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['t3_value'] = t3
        rolling_min = t3.rolling(100, min_periods=1).min()
        rolling_max = t3.rolling(100, min_periods=1).max()
        features['t3_normalized'] = (t3 - rolling_min) / (rolling_max - rolling_min + 1e-10)
        features['t3_slope'] = t3.diff()
        features['t3_acceleration'] = t3.diff().diff()
        features['distance_from_price'] = data['close'] - t3
        features['distance_pct'] = (data['close'] - t3) / t3 * 100
        features['above_t3'] = (data['close'] > t3).astype(int)
        
        return features
    
    def validate_params(self, params: Dict) -> None:
        """Validiert Parameter."""
        for param_name, param_info in self.PARAMETERS.items():
            if param_name in params:
                value = params[param_name]
                if 'min' in param_info and value < param_info['min']:
                    raise ValueError(f"{param_name} must be >= {param_info['min']}")
                if 'max' in param_info and value > param_info['max']:
                    raise ValueError(f"{param_name} must be <= {param_info['max']}")
    
    def get_parameter_grid(self) -> Dict:
        """Generiert Parameter-Grid."""
        grid = {}
        for param_name, param_info in self.PARAMETERS.items():
            if param_info.get('optimize', False):
                grid[param_name] = param_info.get('values', [])
        return grid
    
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed',
                         init_cash: float = 10000, fees: float = 0.0) -> vbt.Portfolio:
        """Führt VectorBT Backtest durch."""
        if strategy_type == 'fixed':
            signals = self.generate_signals_fixed(data, params)
            portfolio = vbt.Portfolio.from_signals(
                data['close'], entries=signals['entries'], exits=signals['exits'],
                tp_stop=signals['tp_levels'], sl_stop=signals['sl_levels'],
                freq='30T', init_cash=init_cash, fees=fees
            )
        else:
            signals = self.generate_signals_dynamic(data, params)
            portfolio = vbt.Portfolio.from_signals(
                data['close'], entries=signals['entries'], exits=signals['exits'],
                freq='30T', init_cash=init_cash, fees=fees
            )
        return portfolio
