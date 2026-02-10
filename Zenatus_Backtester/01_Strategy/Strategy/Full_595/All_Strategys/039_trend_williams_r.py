"""
039 - Williams %R
Momentum-Oszillator der Überkauft/Überverkauft misst
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


class Indicator_WilliamsR:
    """
    Williams %R - Momentum Oscillator
    
    Beschreibung:
        Misst Überkauft/Überverkauft Bedingungen.
        Werte zwischen 0 und -100.
        %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    
    Parameters:
        - period: Lookback-Periode (5-100)
        - overbought: Überkauft-Schwelle (-20 bis 0)
        - oversold: Überverkauft-Schwelle (-100 bis -80)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei %R Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei %R Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'period': {
            'default': 14,
            'min': 5,
            'max': 100,
            'values': [5,7,8,11,13,14,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'Williams %R lookback period'
        },
        'overbought': {
            'default': -20,
            'min': -30,
            'max': 0,
            'values': [-30,-25,-20,-15,-10],
            'optimize': True,
            'ml_feature': True,
            'description': 'Overbought threshold'
        },
        'oversold': {
            'default': -80,
            'min': -100,
            'max': -70,
            'values': [-100,-95,-90,-85,-80,-75,-70],
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
        self.name = "Williams_R"
        self.category = "Momentum"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """
        Berechnet Williams %R.
        
        Formula: %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int}
            
        Returns:
            pd.Series: Williams %R Werte (-100 bis 0)
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Highest High und Lowest Low
        highest_high = high.rolling(window=period, min_periods=1).max()
        lowest_low = low.rolling(window=period, min_periods=1).min()
        
        # Williams %R
        williams_r = ((highest_high - close) / (highest_high - lowest_low + 1e-10)) * -100
        williams_r = williams_r.fillna(-50)
        
        return williams_r
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: Williams %R crosses above oversold level
        Exit: Manual TP/SL
        """
        williams_r = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        # Entry bei %R Cross über oversold
        entries = (williams_r > oversold) & (williams_r.shift(1) <= oversold)
        
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
        signal_strength = abs(williams_r + 50).clip(0, 50) / 50
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - Williams %R-basiert
        
        Entry: Williams %R crosses above oversold
        Exit: Williams %R crosses below overbought
        """
        williams_r = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        
        # Entry bei %R Cross über oversold
        entries = (williams_r > oversold) & (williams_r.shift(1) <= oversold)
        
        # Exit bei %R Cross unter overbought
        exits = (williams_r < overbought) & (williams_r.shift(1) >= overbought)
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'williams_r_overbought_cross'
        
        signal_strength = abs(williams_r + 50).clip(0, 50) / 50
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus Williams %R.
        
        Returns:
            DataFrame mit Features:
            - williams_r_value: Williams %R Wert
            - williams_r_normalized: Normalisiert auf [0, 1]
            - williams_r_slope: Änderungsrate
            - williams_r_overbought: Boolean Flag
            - williams_r_oversold: Boolean Flag
        """
        williams_r = self.calculate(data, params)
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        features = pd.DataFrame(index=data.index)
        features['williams_r_value'] = williams_r
        features['williams_r_normalized'] = (williams_r + 100) / 100
        features['williams_r_slope'] = williams_r.diff()
        features['williams_r_overbought'] = (williams_r > overbought).astype(int)
        features['williams_r_oversold'] = (williams_r < oversold).astype(int)
        
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
