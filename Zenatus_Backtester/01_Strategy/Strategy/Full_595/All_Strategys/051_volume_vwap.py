"""
051 - VWAP (Volume Weighted Average Price)
Der wichtigste Intraday-Volumen-Indikator
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


class Indicator_VWAP:
    """
    VWAP (Volume Weighted Average Price) - Volume Weighted
    
    Beschreibung:
        Volumen-gewichteter Durchschnittspreis.
        VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3
    
    Parameters:
        - reset_period: Reset-Periode in Bars (0 = kein Reset, >0 = Rolling VWAP)
        - std_multiplier: Standardabweichungs-Multiplikator für Bänder (0.5-3.0)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei Price Cross über VWAP, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'reset_period': {
            'default': 0,
            'min': 0,
            'max': 500,
            'values': [0, 50, 100, 200, 300, 400, 500],
            'optimize': True,
            'ml_feature': True,
            'description': 'Reset period (0 = no reset, cumulative)'
        },
        'std_multiplier': {
            'default': 2.0,
            'min': 0.5,
            'max': 3.0,
            'values': [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            'optimize': True,
            'ml_feature': True,
            'description': 'Standard deviation multiplier for bands'
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
        self.name = "VWAP"
        self.category = "Volume"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet VWAP.
        
        Formula:
            Typical Price = (H + L + C) / 3
            VWAP = Cumulative(TP * Volume) / Cumulative(Volume)
            Upper Band = VWAP + (std_dev * multiplier)
            Lower Band = VWAP - (std_dev * multiplier)
        
        Args:
            data: OHLCV DataFrame
            params: {'reset_period': int, 'std_multiplier': float}
            
        Returns:
            pd.DataFrame: vwap, upper_band, lower_band
        """
        self.validate_params(params)
        
        reset_period = params.get('reset_period', self.PARAMETERS['reset_period']['default'])
        std_multiplier = params.get('std_multiplier', self.PARAMETERS['std_multiplier']['default'])
        
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        
        # Typical Price
        tp = (high + low + close) / 3
        
        # VWAP Berechnung
        if reset_period == 0:
            # Cumulative VWAP (kein Reset)
            vwap = (tp * volume).cumsum() / (volume.cumsum() + 1e-10)
        else:
            # Rolling VWAP
            vwap = (tp * volume).rolling(window=reset_period, min_periods=1).sum() / \
                   (volume.rolling(window=reset_period, min_periods=1).sum() + 1e-10)
        
        # Standard Deviation für Bänder
        if reset_period == 0:
            # Expanding std
            price_deviation = (close - vwap) ** 2
            variance = price_deviation.expanding(min_periods=1).mean()
        else:
            # Rolling std
            price_deviation = (close - vwap) ** 2
            variance = price_deviation.rolling(window=reset_period, min_periods=1).mean()
        
        std_dev = np.sqrt(variance)
        
        # VWAP Bands
        upper_band = vwap + (std_dev * std_multiplier)
        lower_band = vwap - (std_dev * std_multiplier)
        
        return pd.DataFrame({
            'vwap': vwap,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'std_dev': std_dev
        }, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: Price crosses above VWAP
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        close = data['close']
        vwap = result['vwap']
        
        # Entry bei Price Cross über VWAP
        entries = (close > vwap) & (close.shift(1) <= vwap.shift(1))
        
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
        
        # Signal Strength
        signal_strength = abs(close - vwap) / (vwap + 1e-10)
        signal_strength = signal_strength.clip(0, 0.05) / 0.05
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - VWAP-basiert
        
        Entry: Price crosses above VWAP
        Exit: Price crosses below VWAP
        """
        result = self.calculate(data, params)
        close = data['close']
        vwap = result['vwap']
        
        # Entry bei Price Cross über VWAP
        entries = (close > vwap) & (close.shift(1) <= vwap.shift(1))
        
        # Exit bei Price Cross unter VWAP
        exits = (close < vwap) & (close.shift(1) >= vwap.shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'vwap_reverse_cross'
        
        signal_strength = abs(close - vwap) / (vwap + 1e-10)
        signal_strength = signal_strength.clip(0, 0.05) / 0.05
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus VWAP.
        
        Returns:
            DataFrame mit Features:
            - vwap_value: VWAP Wert
            - vwap_upper: Upper Band
            - vwap_lower: Lower Band
            - vwap_distance: Distance from VWAP
            - vwap_position: Position (above/below)
            - vwap_band_width: Band Width
        """
        result = self.calculate(data, params)
        close = data['close']
        
        features = pd.DataFrame(index=data.index)
        features['vwap_value'] = result['vwap']
        features['vwap_upper'] = result['upper_band']
        features['vwap_lower'] = result['lower_band']
        features['vwap_distance'] = (close - result['vwap']) / result['vwap']
        features['vwap_position'] = (close > result['vwap']).astype(int)
        features['vwap_band_width'] = (result['upper_band'] - result['lower_band']) / result['vwap']
        
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
