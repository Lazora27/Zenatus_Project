"""
047 - On-Balance Volume (OBV)
Kumulatives Volumen-Momentum
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


class Indicator_OBV:
    """
    On-Balance Volume (OBV) - Volume Momentum
    
    Beschreibung:
        Kumulatives Volumen basierend auf Preisbewegung.
        Wenn Close > Close[prev]: OBV += Volume
        Wenn Close < Close[prev]: OBV -= Volume
        Wenn Close == Close[prev]: OBV unverändert
    
    Parameters:
        - signal_period: EMA für Signal-Linie (5-50)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei OBV Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei OBV Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'signal_period': {
            'default': 20,
            'min': 5,
            'max': 50,
            'values': [5,7,8,11,13,14,17,19,20,21,23,29,31,34,37,41,43,47],
            'optimize': True,
            'ml_feature': True,
            'description': 'EMA period for signal line'
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
        self.name = "OBV"
        self.category = "Volume"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet On-Balance Volume.
        
        Formula:
            If Close > Close[prev]: OBV += Volume
            If Close < Close[prev]: OBV -= Volume
            If Close == Close[prev]: OBV unchanged
        
        Args:
            data: OHLCV DataFrame
            params: {'signal_period': int}
            
        Returns:
            pd.DataFrame: obv, obv_signal, obv_divergence
        """
        self.validate_params(params)
        
        signal_period = params.get('signal_period', self.PARAMETERS['signal_period']['default'])
        
        close = data['close']
        volume = data['volume']
        
        # OBV Berechnung
        obv = pd.Series(0.0, index=data.index)
        
        for i in range(1, len(data)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        # Signal Line (EMA)
        obv_signal = obv.ewm(span=signal_period, adjust=False).mean()
        
        # Divergence
        obv_divergence = obv - obv_signal
        
        return pd.DataFrame({
            'obv': obv,
            'obv_signal': obv_signal,
            'obv_divergence': obv_divergence
        }, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: OBV crosses above Signal Line
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        obv = result['obv']
        obv_signal = result['obv_signal']
        
        # Entry bei OBV Cross über Signal
        entries = (obv > obv_signal) & (obv.shift(1) <= obv_signal.shift(1))
        
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
        signal_strength = abs(result['obv_divergence']).clip(0, 1000000) / 1000000
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - OBV-basiert
        
        Entry: OBV crosses above Signal Line
        Exit: OBV crosses below Signal Line
        """
        result = self.calculate(data, params)
        obv = result['obv']
        obv_signal = result['obv_signal']
        
        # Entry bei OBV Cross über Signal
        entries = (obv > obv_signal) & (obv.shift(1) <= obv_signal.shift(1))
        
        # Exit bei OBV Cross unter Signal
        exits = (obv < obv_signal) & (obv.shift(1) >= obv_signal.shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'obv_signal_cross'
        
        signal_strength = abs(result['obv_divergence']).clip(0, 1000000) / 1000000
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus OBV.
        
        Returns:
            DataFrame mit Features:
            - obv_value: OBV Wert
            - obv_signal: Signal Line
            - obv_divergence: OBV - Signal
            - obv_slope: OBV Änderungsrate
            - obv_trend: Trend Direction
            - obv_volume_ratio: OBV / Volume
        """
        result = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        features['obv_value'] = result['obv']
        features['obv_signal'] = result['obv_signal']
        features['obv_divergence'] = result['obv_divergence']
        features['obv_slope'] = result['obv'].diff()
        features['obv_trend'] = (result['obv'] > result['obv_signal']).astype(int)
        features['obv_volume_ratio'] = result['obv'] / (data['volume'].rolling(20).sum() + 1e-10)
        
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
