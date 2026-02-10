"""
037 - Rate of Change (ROC)
Misst prozentuale Preisänderung über N Perioden
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


class Indicator_ROC:
    """
    Rate of Change (ROC) - Momentum
    
    Beschreibung:
        Misst die prozentuale Preisänderung über N Perioden.
        ROC = ((Close - Close[n]) / Close[n]) * 100
    
    Parameters:
        - period: Lookback-Periode (5-100)
        - threshold: Signal-Schwelle (0-10)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei ROC Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei ROC Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'period': {
            'default': 12,
            'min': 5,
            'max': 100,
            'values': [5,7,8,11,12,13,14,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'ROC lookback period'
        },
        'threshold': {
            'default': 0,
            'min': -10,
            'max': 10,
            'values': [-5,-3,-2,-1,0,1,2,3,5],
            'optimize': True,
            'ml_feature': True,
            'description': 'Signal threshold'
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
        self.name = "ROC"
        self.category = "Momentum"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """
        Berechnet Rate of Change.
        
        Formula: ROC = ((Close - Close[n]) / Close[n]) * 100
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int}
            
        Returns:
            pd.Series: ROC Werte in Prozent
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        close = data['close']
        
        # ROC Berechnung
        roc = ((close - close.shift(period)) / (close.shift(period) + 1e-10)) * 100
        roc = roc.fillna(0)
        
        return roc
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: ROC crosses above threshold
        Exit: Manual TP/SL
        """
        roc = self.calculate(data, params)
        threshold = params.get('threshold', self.PARAMETERS['threshold']['default'])
        
        # Entry bei ROC Cross über threshold
        entries = (roc > threshold) & (roc.shift(1) <= threshold)
        
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
        signal_strength = abs(roc).clip(0, 20) / 20
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - ROC-basiert
        
        Entry: ROC crosses above threshold
        Exit: ROC crosses below -threshold
        """
        roc = self.calculate(data, params)
        threshold = params.get('threshold', self.PARAMETERS['threshold']['default'])
        
        # Entry bei ROC Cross über threshold
        entries = (roc > threshold) & (roc.shift(1) <= threshold)
        
        # Exit bei ROC Cross unter -threshold
        exits = (roc < -threshold) & (roc.shift(1) >= -threshold)
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'roc_reverse_cross'
        
        signal_strength = abs(roc).clip(0, 20) / 20
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus ROC.
        
        Returns:
            DataFrame mit Features:
            - roc_value: ROC Wert
            - roc_normalized: Normalisiert
            - roc_slope: Änderungsrate
            - roc_positive: Boolean Flag
        """
        roc = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        features['roc_value'] = roc
        features['roc_normalized'] = roc.clip(-20, 20) / 20
        features['roc_slope'] = roc.diff()
        features['roc_positive'] = (roc > 0).astype(int)
        
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
