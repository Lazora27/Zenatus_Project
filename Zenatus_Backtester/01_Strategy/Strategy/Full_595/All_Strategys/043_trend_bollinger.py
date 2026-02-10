"""
043 - Bollinger Bands
Volatilitäts-Indikator mit dynamischen Bändern
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


class Indicator_BollingerBands:
    """
    Bollinger Bands - Volatility/Trend
    
    Beschreibung:
        Volatilitäts-Bänder um einen Moving Average.
        Middle Band = SMA(period)
        Upper Band = Middle + (std_dev * multiplier)
        Lower Band = Middle - (std_dev * multiplier)
    
    Parameters:
        - period: SMA Periode (5-100)
        - multiplier: Standardabweichungs-Multiplikator (0.5-5.0)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei Band Touch, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei Lower Band, Exit bei Upper Band
    """
    
    PARAMETERS = {
        'period': {
            'default': 20,
            'min': 5,
            'max': 100,
            'values': [5,7,8,11,13,14,17,19,20,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'SMA period for middle band'
        },
        'multiplier': {
            'default': 2.0,
            'min': 0.5,
            'max': 5.0,
            'values': [0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.25,2.5,2.75,3.0,3.5,4.0,5.0],
            'optimize': True,
            'ml_feature': True,
            'description': 'Standard deviation multiplier'
        },
        'tp_pips': {
            'default': 50,
            'min': 20,
            'max': 200,
            'values': [30,40,50,60,75,100,125,150,200],
            'optimize': True,
            'ml_feature': False,
            'description': 'Take Profit in pips'
        },
        'sl_pips': {
            'default': 25,
            'min': 10,
            'max': 100,
            'values': [10,15,20,25,30,40,50],
            'optimize': True,
            'ml_feature': False,
            'description': 'Stop Loss in pips'
        }
    }
    
    def __init__(self):
        self.name = "BollingerBands"
        self.category = "Volatility"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet Bollinger Bands.
        
        Formula:
            Middle = SMA(close, period)
            Upper = Middle + (std_dev * multiplier)
            Lower = Middle - (std_dev * multiplier)
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int, 'multiplier': float}
            
        Returns:
            pd.DataFrame: upper, middle, lower, bandwidth, %b
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        multiplier = params.get('multiplier', self.PARAMETERS['multiplier']['default'])
        
        close = data['close']
        
        # Middle Band (SMA)
        middle = close.rolling(window=period, min_periods=1).mean()
        
        # Standard Deviation
        std_dev = close.rolling(window=period, min_periods=1).std()
        
        # Upper and Lower Bands
        upper = middle + (std_dev * multiplier)
        lower = middle - (std_dev * multiplier)
        
        # Bandwidth (Volatility Measure)
        bandwidth = (upper - lower) / (middle + 1e-10)
        
        # %B (Position within bands)
        percent_b = (close - lower) / (upper - lower + 1e-10)
        
        return pd.DataFrame({
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'bandwidth': bandwidth,
            'percent_b': percent_b
        }, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: Price touches or crosses below Lower Band
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        close = data['close']
        
        # Entry bei Touch/Cross Lower Band
        entries = (close <= result['lower']) & (close.shift(1) > result['lower'].shift(1))
        
        tp_pips = params.get('tp_pips', self.PARAMETERS['tp_pips']['default'])
        sl_pips = params.get('sl_pips', self.PARAMETERS['sl_pips']['default'])
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
        
        # Dummy TP/SL levels
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        
        # Signal Strength basierend auf %B
        signal_strength = abs(result['percent_b'] - 0.5).clip(0, 0.5) / 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - Bollinger Bands-basiert
        
        Entry: Price touches Lower Band
        Exit: Price touches Upper Band or Middle Band
        """
        result = self.calculate(data, params)
        close = data['close']
        
        # Entry bei Lower Band Touch
        entries = (close <= result['lower']) & (close.shift(1) > result['lower'].shift(1))
        
        # Exit bei Upper Band oder Middle Band Touch
        exits = ((close >= result['upper']) & (close.shift(1) < result['upper'].shift(1))) | \
                ((close >= result['middle']) & (close.shift(1) < result['middle'].shift(1)))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'bollinger_band_exit'
        
        signal_strength = abs(result['percent_b'] - 0.5).clip(0, 0.5) / 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus Bollinger Bands.
        
        Returns:
            DataFrame mit Features:
            - bb_upper: Upper Band
            - bb_middle: Middle Band
            - bb_lower: Lower Band
            - bb_bandwidth: Bandwidth (Volatility)
            - bb_percent_b: %B Position
            - bb_squeeze: Squeeze Indicator
        """
        result = self.calculate(data, params)
        close = data['close']
        
        features = pd.DataFrame(index=data.index)
        features['bb_upper'] = result['upper']
        features['bb_middle'] = result['middle']
        features['bb_lower'] = result['lower']
        features['bb_bandwidth'] = result['bandwidth']
        features['bb_percent_b'] = result['percent_b']
        
        # Squeeze: Bandwidth < 20-period low of bandwidth
        features['bb_squeeze'] = (result['bandwidth'] < 
                                  result['bandwidth'].rolling(20).min()).astype(int)
        
        # Distance from bands
        features['bb_distance_upper'] = (result['upper'] - close) / close
        features['bb_distance_lower'] = (close - result['lower']) / close
        
        return features
    
    def validate_params(self, params: Dict) -> None:
        """Validiert Parameter-Ranges."""
        for key, value in params.items():
            if key in self.PARAMETERS:
                param_def = self.PARAMETERS[key]
                if 'min' in param_def and value < param_def['min']:
                    raise ValueError(f"{key} = {value} below minimum {param_def['min']}")
                if 'max' in param_def and value > param_def['max']:
                    raise ValueError(f"{key} = {value} above maximum {param_def['max']}")
    
    def get_parameter_grid(self) -> Dict:
        """Gibt Parameter-Grid für Optimierung zurück."""
        return {
            key: value.get('values', [])
            for key, value in self.PARAMETERS.items()
            if value.get('optimize', False)
        }
    
    def backtest_vectorbt(
        self,
        data: pd.DataFrame,
        params: Dict,
        strategy_type: str = 'fixed',
        init_cash: float = 10000,
        fees: float = 0.0
    ) -> vbt.Portfolio:
        """Führt VectorBT Backtest durch."""
        if strategy_type == 'fixed':
            signals = self.generate_signals_fixed(data, params)
        else:
            signals = self.generate_signals_dynamic(data, params)
        
        portfolio = vbt.Portfolio.from_signals(
            data['close'],
            entries=signals['entries'],
            exits=signals['exits'],
            tp_stop=signals.get('tp_levels'),
            sl_stop=signals.get('sl_levels'),
            freq='30T',
            init_cash=init_cash,
            fees=fees
        )
        
        return portfolio
