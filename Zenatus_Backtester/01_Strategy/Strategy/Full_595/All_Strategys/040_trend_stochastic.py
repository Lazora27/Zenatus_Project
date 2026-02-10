"""
040 - Stochastic Oscillator
Klassischer Momentum-Indikator mit %K und %D Linien
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


class Indicator_Stochastic:
    """
    Stochastic Oscillator - Momentum
    
    Beschreibung:
        Vergleicht Close-Preis mit High/Low Range über N Perioden.
        %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
        %D = SMA(%K, smooth_period)
    
    Parameters:
        - period: Lookback-Periode (5-100)
        - smooth_k: %K Glättung (1-10)
        - smooth_d: %D Glättung (1-10)
        - overbought: Überkauft-Schwelle (70-90)
        - oversold: Überverkauft-Schwelle (10-30)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei %K/%D Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei %K/%D Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'period': {
            'default': 14,
            'min': 5,
            'max': 100,
            'values': [5,7,8,11,13,14,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'Stochastic lookback period'
        },
        'smooth_k': {
            'default': 3,
            'min': 1,
            'max': 10,
            'values': [1,2,3,4,5,6,7,8,9,10],
            'optimize': True,
            'ml_feature': True,
            'description': '%K smoothing period'
        },
        'smooth_d': {
            'default': 3,
            'min': 1,
            'max': 10,
            'values': [1,2,3,4,5,6,7,8,9,10],
            'optimize': True,
            'ml_feature': True,
            'description': '%D smoothing period'
        },
        'overbought': {
            'default': 80,
            'min': 70,
            'max': 90,
            'values': [70,75,80,85,90],
            'optimize': True,
            'ml_feature': True,
            'description': 'Overbought threshold'
        },
        'oversold': {
            'default': 20,
            'min': 10,
            'max': 30,
            'values': [10,15,20,25,30],
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
        self.name = "Stochastic"
        self.category = "Momentum"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet Stochastic Oscillator.
        
        Formula:
            %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
            %D = SMA(%K, smooth_d)
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int, 'smooth_k': int, 'smooth_d': int}
            
        Returns:
            pd.DataFrame: %K und %D Werte
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        smooth_k = params.get('smooth_k', self.PARAMETERS['smooth_k']['default'])
        smooth_d = params.get('smooth_d', self.PARAMETERS['smooth_d']['default'])
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Highest High und Lowest Low
        highest_high = high.rolling(window=period, min_periods=1).max()
        lowest_low = low.rolling(window=period, min_periods=1).min()
        
        # %K (Fast Stochastic)
        k_fast = ((close - lowest_low) / (highest_high - lowest_low + 1e-10)) * 100
        
        # %K (Slow Stochastic - geglättet)
        k_slow = k_fast.rolling(window=smooth_k, min_periods=1).mean()
        
        # %D (Signal Line)
        d = k_slow.rolling(window=smooth_d, min_periods=1).mean()
        
        k_slow = k_slow.fillna(50)
        d = d.fillna(50)
        
        return pd.DataFrame({'k': k_slow, 'd': d}, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: %K crosses above %D in oversold zone
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        k = result['k']
        d = result['d']
        
        # Entry bei %K Cross über %D in oversold Zone
        entries = (k > d) & (k.shift(1) <= d.shift(1)) & (k < oversold)
        
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
        
        # Signal Strength basierend auf K-D Divergenz
        signal_strength = abs(k - d).clip(0, 50) / 50
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - Stochastic-basiert
        
        Entry: %K crosses above %D in oversold zone
        Exit: %K crosses below %D in overbought zone
        """
        result = self.calculate(data, params)
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        
        k = result['k']
        d = result['d']
        
        # Entry bei %K Cross über %D in oversold Zone
        entries = (k > d) & (k.shift(1) <= d.shift(1)) & (k < oversold)
        
        # Exit bei %K Cross unter %D in overbought Zone
        exits = (k < d) & (k.shift(1) >= d.shift(1)) & (k > overbought)
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'stochastic_overbought_cross'
        
        signal_strength = abs(k - d).clip(0, 50) / 50
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus Stochastic.
        
        Returns:
            DataFrame mit Features:
            - stoch_k: %K Wert
            - stoch_d: %D Wert
            - stoch_k_normalized: Normalisiert
            - stoch_d_normalized: Normalisiert
            - stoch_divergence: K-D Divergenz
            - stoch_overbought: Boolean Flag
            - stoch_oversold: Boolean Flag
        """
        result = self.calculate(data, params)
        overbought = params.get('overbought', self.PARAMETERS['overbought']['default'])
        oversold = params.get('oversold', self.PARAMETERS['oversold']['default'])
        
        k = result['k']
        d = result['d']
        
        features = pd.DataFrame(index=data.index)
        features['stoch_k'] = k
        features['stoch_d'] = d
        features['stoch_k_normalized'] = k / 100
        features['stoch_d_normalized'] = d / 100
        features['stoch_divergence'] = k - d
        features['stoch_overbought'] = (k > overbought).astype(int)
        features['stoch_oversold'] = (k < oversold).astype(int)
        
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
