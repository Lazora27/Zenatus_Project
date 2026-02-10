"""
042 - MACD (Moving Average Convergence Divergence)
Klassischer Trend-Following Momentum-Indikator
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


class Indicator_MACD:
    """
    MACD (Moving Average Convergence Divergence) - Trend/Momentum
    
    Beschreibung:
        Zeigt Beziehung zwischen zwei EMAs.
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD, signal_period)
        Histogram = MACD - Signal
    
    Parameters:
        - fast_period: Schnelle EMA (5-50)
        - slow_period: Langsame EMA (10-100)
        - signal_period: Signal-Linie EMA (3-20)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei MACD Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei MACD Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'fast_period': {
            'default': 12,
            'min': 5,
            'max': 50,
            'values': [5,7,8,10,11,12,13,14,17,19,21,23,29,31,34,37,41,43,47],
            'optimize': True,
            'ml_feature': True,
            'description': 'Fast EMA period'
        },
        'slow_period': {
            'default': 26,
            'min': 10,
            'max': 100,
            'values': [13,17,19,21,23,26,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'Slow EMA period'
        },
        'signal_period': {
            'default': 9,
            'min': 3,
            'max': 20,
            'values': [3,5,7,8,9,11,13,14,17,19],
            'optimize': True,
            'ml_feature': True,
            'description': 'Signal line EMA period'
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
        self.name = "MACD"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet MACD.
        
        Formula:
            MACD = EMA(fast) - EMA(slow)
            Signal = EMA(MACD, signal_period)
            Histogram = MACD - Signal
        
        Args:
            data: OHLCV DataFrame
            params: {'fast_period': int, 'slow_period': int, 'signal_period': int}
            
        Returns:
            pd.DataFrame: MACD, Signal, Histogram
        """
        self.validate_params(params)
        
        fast_period = params.get('fast_period', self.PARAMETERS['fast_period']['default'])
        slow_period = params.get('slow_period', self.PARAMETERS['slow_period']['default'])
        signal_period = params.get('signal_period', self.PARAMETERS['signal_period']['default'])
        
        close = data['close']
        
        # EMAs
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()
        
        # MACD Line
        macd_line = ema_fast - ema_slow
        
        # Signal Line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: MACD crosses above Signal Line
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        macd = result['macd']
        signal = result['signal']
        
        # Entry bei MACD Cross über Signal
        entries = (macd > signal) & (macd.shift(1) <= signal.shift(1))
        
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
        
        # Signal Strength basierend auf Histogram
        signal_strength = abs(result['histogram']).clip(0, 0.01) / 0.01
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - MACD-basiert
        
        Entry: MACD crosses above Signal Line
        Exit: MACD crosses below Signal Line
        """
        result = self.calculate(data, params)
        macd = result['macd']
        signal = result['signal']
        
        # Entry bei MACD Cross über Signal
        entries = (macd > signal) & (macd.shift(1) <= signal.shift(1))
        
        # Exit bei MACD Cross unter Signal
        exits = (macd < signal) & (macd.shift(1) >= signal.shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'macd_signal_cross'
        
        signal_strength = abs(result['histogram']).clip(0, 0.01) / 0.01
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus MACD.
        
        Returns:
            DataFrame mit Features:
            - macd_line: MACD Linie
            - macd_signal: Signal Linie
            - macd_histogram: Histogram
            - macd_histogram_slope: Histogram Änderung
            - macd_divergence: MACD - Signal
            - macd_cross_bullish: Bullish Cross Flag
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        features['macd_line'] = result['macd']
        features['macd_signal'] = result['signal']
        features['macd_histogram'] = result['histogram']
        features['macd_histogram_slope'] = result['histogram'].diff()
        features['macd_divergence'] = result['macd'] - result['signal']
        features['macd_cross_bullish'] = ((result['macd'] > result['signal']) & 
                                          (result['macd'].shift(1) <= result['signal'].shift(1))).astype(int)
        
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
        
        # Zusätzliche Validierung: fast < slow
        if 'fast_period' in params and 'slow_period' in params:
            if params['fast_period'] >= params['slow_period']:
                raise ValueError("fast_period must be less than slow_period")
    
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
