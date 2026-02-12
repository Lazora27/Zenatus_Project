"""
041 - Relative Strength Index (RSI)
Der wichtigste Momentum-Oszillator für Überkauft/Überverkauft
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


class Indicator_RSI:
    """
    Relative Strength Index (RSI) - Momentum
    
    Beschreibung:
        Misst die Geschwindigkeit und Änderung von Preisbewegungen.
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        Werte: 0-100 (>70 überkauft, <30 überverkauft)
    
    Parameters:
        - period: Lookback-Periode (2-100)
        - overbought: Überkauft-Schwelle (60-90)
        - oversold: Überverkauft-Schwelle (10-40)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei RSI Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei RSI Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'period': {
            'default': 14,
            'min': 2,
            'max': 100,
            'values': [2,3,5,7,8,11,13,14,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'RSI lookback period'
        },
        'overbought': {
            'default': 70,
            'min': 60,
            'max': 90,
            'values': [60,65,70,75,80,85,90],
            'optimize': True,
            'ml_feature': True,
            'description': 'Overbought threshold'
        },
        'oversold': {
            'default': 30,
            'min': 10,
            'max': 40,
            'values': [10,15,20,25,30,35,40],
            'optimize': True,
            'ml_feature': True,
            'description': 'Oversold threshold'
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
        self.name = "RSI"
        self.category = "Momentum"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """
        Berechnet Relative Strength Index.
        
        Formula:
            RS = Average Gain / Average Loss
            RSI = 100 - (100 / (1 + RS))
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int}
            
        Returns:
            pd.Series: RSI Werte (0-100)
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        close = data['close']
        
        # Berechne Preisänderungen
        delta = close.diff()
        
        # Separate Gains und Losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Wilder's Smoothing (EMA mit alpha = 1/period)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
        # Relative Strength
        rs = avg_gain / (avg_loss + 1e-10)
        
        # RSI
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        
        return rsi
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: RSI crosses above oversold level
        Exit: Manual TP/SL
        """
        rsi = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        # Entry bei RSI Cross über oversold
        entries = (rsi > oversold) & (rsi.shift(1) <= oversold)
        
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
        signal_strength = abs(rsi - 50).clip(0, 50) / 50
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - RSI-basiert
        
        Entry: RSI crosses above oversold
        Exit: RSI crosses below overbought
        """
        rsi = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        
        # Entry bei RSI Cross über oversold
        entries = (rsi > oversold) & (rsi.shift(1) <= oversold)
        
        # Exit bei RSI Cross unter overbought
        exits = (rsi < overbought) & (rsi.shift(1) >= overbought)
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'rsi_overbought_cross'
        
        signal_strength = abs(rsi - 50).clip(0, 50) / 50
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus RSI.
        
        Returns:
            DataFrame mit Features:
            - rsi_value: RSI Wert
            - rsi_normalized: Normalisiert auf [0, 1]
            - rsi_slope: Änderungsrate
            - rsi_overbought: Boolean Flag
            - rsi_oversold: Boolean Flag
            - rsi_divergence: Abweichung von 50
        """
        rsi = self.calculate(data, params)
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        features = pd.DataFrame(index=data.index)
        features['rsi_value'] = rsi
        features['rsi_normalized'] = rsi / 100
        features['rsi_slope'] = rsi.diff()
        features['rsi_overbought'] = (rsi > overbought).astype(int)
        features['rsi_oversold'] = (rsi < oversold).astype(int)
        features['rsi_divergence'] = rsi - 50
        
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
