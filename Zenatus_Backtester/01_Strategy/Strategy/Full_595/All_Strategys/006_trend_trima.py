"""
006 - Triangular Moving Average (TRIMA)
Doppelt geglätteter Moving Average
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


class Indicator_TRIMA:
    """
    Triangular Moving Average (TRIMA) - Trend
    
    Beschreibung:
        Doppelt geglätteter SMA. Berechnet SMA von SMA.
        Sehr glatt, starker Lag, gut für langfristige Trends.
    
    Formula:
        TRIMA = SMA(SMA(Close, period/2), period/2)
    
    Parameters:
        - period: Lookback-Periode (2-200, muss gerade sein)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    """
    
    PARAMETERS = {
        'period': {
            'default': 20,
            'min': 4,
            'max': 200,
            'values': [8,12,16,20,24,28,32,36,40,44,48,52,56,60,68,72,80,88],
            'step': 2,
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
        self.name = "TRIMA"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """Berechnet Triangular Moving Average."""
        self.validate_params(params)
        period = params.get('period', self.PARAMETERS['period']['default'])
        
        # Stelle sicher dass period gerade ist
        if period % 2 != 0:
            period += 1
        
        half_period = period // 2
        
        # Erste SMA
        sma1 = data['close'].rolling(window=half_period, min_periods=1).mean()
        # Zweite SMA von SMA1
        trima = sma1.rolling(window=half_period, min_periods=1).mean()
        
        return trima
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategie."""
        trima = self.calculate(data, params)
        entries = (data['close'] > trima) & (data['close'].shift(1) <= trima.shift(1))
        
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
        signal_strength = abs(data['close'] - trima) / trima
        signal_strength = signal_strength.clip(0, 1)
        
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 
                'sl_levels': sl_levels, 'signal_strength': signal_strength}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic Exit Strategie."""
        trima = self.calculate(data, params)
        entries = (data['close'] > trima) & (data['close'].shift(1) <= trima.shift(1))
        exits = (data['close'] < trima) & (data['close'].shift(1) >= trima.shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'trima_reverse_cross'
        
        signal_strength = abs(data['close'] - trima) / trima
        signal_strength = signal_strength.clip(0, 1)
        
        return {'entries': entries, 'exits': exits, 'exit_reason': exit_reason, 
                'signal_strength': signal_strength}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extrahiert ML-Features."""
        trima = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['trima_value'] = trima
        rolling_min = trima.rolling(100, min_periods=1).min()
        rolling_max = trima.rolling(100, min_periods=1).max()
        features['trima_normalized'] = (trima - rolling_min) / (rolling_max - rolling_min + 1e-10)
        features['trima_slope'] = trima.diff()
        features['trima_acceleration'] = trima.diff().diff()
        features['distance_from_price'] = data['close'] - trima
        features['distance_pct'] = (data['close'] - trima) / trima * 100
        features['above_trima'] = (data['close'] > trima).astype(int)
        
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
                grid[param_name] = param_info.get('values', list(range(
                    param_info['min'], param_info['max'] + 1, param_info['step']
                )))
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
