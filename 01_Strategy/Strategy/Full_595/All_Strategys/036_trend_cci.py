"""
036 - Commodity Channel Index (CCI)
Misst Abweichung vom statistischen Durchschnitt
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


class Indicator_CCI:
    """
    Commodity Channel Index (CCI) - Momentum/Trend
    
    Beschreibung:
        Misst die Abweichung des Preises vom statistischen Durchschnitt.
        Werte über +100 = überkauft, unter -100 = überverkauft.
    
    Parameters:
        - period: Lookback-Periode (5-100)
        - overbought: Überkauft-Schwelle (100-300)
        - oversold: Überverkauft-Schwelle (-300 bis -100)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei CCI Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei CCI Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'period': {
            'default': 20,
            'min': 5,
            'max': 100,
            'values': [5,7,8,11,13,14,17,19,20,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'CCI lookback period'
        },
        'overbought': {
            'default': 100,
            'min': 50,
            'max': 300,
            'values': [50,75,100,125,150,175,200,250,300],
            'optimize': True,
            'ml_feature': True,
            'description': 'Overbought threshold'
        },
        'oversold': {
            'default': -100,
            'min': -300,
            'max': -50,
            'values': [-300,-250,-200,-175,-150,-125,-100,-75,-50],
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
        self.name = "CCI"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """
        Berechnet Commodity Channel Index.
        
        Formula:
            TP = (High + Low + Close) / 3
            SMA = SMA(TP, period)
            MAD = Mean Absolute Deviation
            CCI = (TP - SMA) / (0.015 * MAD)
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int}
            
        Returns:
            pd.Series: CCI Werte
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        
        # Typical Price
        tp = (data['high'] + data['low'] + data['close']) / 3
        
        # Simple Moving Average of TP
        sma_tp = tp.rolling(window=period, min_periods=1).mean()
        
        # Mean Absolute Deviation
        mad = tp.rolling(window=period, min_periods=1).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        
        # CCI
        cci = (tp - sma_tp) / (0.015 * mad)
        cci = cci.fillna(0)
        
        return cci
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: CCI crosses above oversold level
        Exit: Manual TP/SL
        """
        cci = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        # Entry bei CCI Cross über oversold
        entries = (cci > oversold) & (cci.shift(1) <= oversold)
        
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
        
        # Signal Strength basierend auf CCI-Wert
        signal_strength = abs(cci).clip(0, 200) / 200
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - CCI-basiert
        
        Entry: CCI crosses above oversold
        Exit: CCI crosses below overbought
        """
        cci = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        
        # Entry bei CCI Cross über oversold
        entries = (cci > oversold) & (cci.shift(1) <= oversold)
        
        # Exit bei CCI Cross unter overbought
        exits = (cci < overbought) & (cci.shift(1) >= overbought)
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'cci_overbought_cross'
        
        signal_strength = abs(cci).clip(0, 200) / 200
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus CCI.
        
        Returns:
            DataFrame mit Features:
            - cci_value: CCI Wert
            - cci_normalized: Normalisiert auf [-1, 1]
            - cci_slope: Änderungsrate
            - cci_overbought: Boolean Flag
            - cci_oversold: Boolean Flag
        """
        cci = self.calculate(data, params)
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        features = pd.DataFrame(index=data.index)
        features['cci_value'] = cci
        features['cci_normalized'] = cci.clip(-200, 200) / 200
        features['cci_slope'] = cci.diff()
        features['cci_overbought'] = (cci > overbought).astype(int)
        features['cci_oversold'] = (cci < oversold).astype(int)
        
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
        """
        Führt VectorBT Backtest durch.
        
        Args:
            data: OHLCV DataFrame
            params: Parameter Dictionary
            strategy_type: 'fixed' oder 'dynamic'
            init_cash: Startkapital
            fees: Trading Fees
            
        Returns:
            vbt.Portfolio Objekt
        """
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
