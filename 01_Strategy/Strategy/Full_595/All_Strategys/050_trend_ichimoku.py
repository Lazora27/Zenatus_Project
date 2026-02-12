"""
050 - Ichimoku Cloud (Simplified)
Komplexes Multi-Component Trend-System
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


class Indicator_Ichimoku:
    """
    Ichimoku Cloud - Multi-Component Trend System
    
    Beschreibung:
        Komplexes System mit 5 Komponenten:
        - Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        - Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        - Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted +26
        - Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted +26
        - Chikou Span (Lagging Span): Close, shifted -26
    
    Parameters:
        - tenkan_period: Tenkan-sen Periode (5-20)
        - kijun_period: Kijun-sen Periode (10-50)
        - senkou_period: Senkou Span B Periode (20-100)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei Tenkan/Kijun Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei Cross, Exit bei Reverse Cross
    """
    
    PARAMETERS = {
        'tenkan_period': {
            'default': 9,
            'min': 5,
            'max': 20,
            'values': [5,7,8,9,11,13,14,17,19],
            'optimize': True,
            'ml_feature': True,
            'description': 'Tenkan-sen period'
        },
        'kijun_period': {
            'default': 26,
            'min': 10,
            'max': 50,
            'values': [13,17,19,21,23,26,29,31,34,37,41,43,47],
            'optimize': True,
            'ml_feature': True,
            'description': 'Kijun-sen period'
        },
        'senkou_period': {
            'default': 52,
            'min': 20,
            'max': 100,
            'values': [34,37,41,43,47,52,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'Senkou Span B period'
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
        self.name = "Ichimoku"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet Ichimoku Cloud Komponenten.
        
        Formula:
            Tenkan = (High[9] + Low[9]) / 2
            Kijun = (High[26] + Low[26]) / 2
            Senkou A = (Tenkan + Kijun) / 2, shifted +26
            Senkou B = (High[52] + Low[52]) / 2, shifted +26
            Chikou = Close, shifted -26
        
        Args:
            data: OHLCV DataFrame
            params: {'tenkan_period': int, 'kijun_period': int, 'senkou_period': int}
            
        Returns:
            pd.DataFrame: tenkan, kijun, senkou_a, senkou_b, chikou
        """
        self.validate_params(params)
        
        tenkan_period = params.get('tenkan_period', self.PARAMETERS['tenkan_period']['default'])
        kijun_period = params.get('kijun_period', self.PARAMETERS['kijun_period']['default'])
        senkou_period = params.get('senkou_period', self.PARAMETERS['senkou_period']['default'])
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Tenkan-sen (Conversion Line)
        tenkan_high = high.rolling(window=tenkan_period, min_periods=1).max()
        tenkan_low = low.rolling(window=tenkan_period, min_periods=1).min()
        tenkan = (tenkan_high + tenkan_low) / 2
        
        # Kijun-sen (Base Line)
        kijun_high = high.rolling(window=kijun_period, min_periods=1).max()
        kijun_low = low.rolling(window=kijun_period, min_periods=1).min()
        kijun = (kijun_high + kijun_low) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_a = ((tenkan + kijun) / 2).shift(kijun_period)
        
        # Senkou Span B (Leading Span B)
        senkou_high = high.rolling(window=senkou_period, min_periods=1).max()
        senkou_low = low.rolling(window=senkou_period, min_periods=1).min()
        senkou_b = ((senkou_high + senkou_low) / 2).shift(kijun_period)
        
        # Chikou Span (Lagging Span)
        chikou = close.shift(-kijun_period)
        
        return pd.DataFrame({
            'tenkan': tenkan,
            'kijun': kijun,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b,
            'chikou': chikou
        }, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: Tenkan crosses above Kijun
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        tenkan = result['tenkan']
        kijun = result['kijun']
        
        # Entry bei Tenkan Cross über Kijun
        entries = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
        
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
        signal_strength = abs(tenkan - kijun) / (kijun + 1e-10)
        signal_strength = signal_strength.clip(0, 0.1) / 0.1
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - Ichimoku-basiert
        
        Entry: Tenkan crosses above Kijun
        Exit: Tenkan crosses below Kijun
        """
        result = self.calculate(data, params)
        tenkan = result['tenkan']
        kijun = result['kijun']
        
        # Entry bei Tenkan Cross über Kijun
        entries = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
        
        # Exit bei Tenkan Cross unter Kijun
        exits = (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'ichimoku_reverse_cross'
        
        signal_strength = abs(tenkan - kijun) / (kijun + 1e-10)
        signal_strength = signal_strength.clip(0, 0.1) / 0.1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus Ichimoku.
        
        Returns:
            DataFrame mit Features:
            - ichimoku_tenkan: Tenkan-sen
            - ichimoku_kijun: Kijun-sen
            - ichimoku_senkou_a: Senkou Span A
            - ichimoku_senkou_b: Senkou Span B
            - ichimoku_cloud_thickness: Cloud Dicke
            - ichimoku_tk_cross: Tenkan/Kijun Cross
            - ichimoku_price_vs_cloud: Preis vs Cloud Position
        """
        result = self.calculate(data, params)
        close = data['close']
        
        features = pd.DataFrame(index=data.index)
        features['ichimoku_tenkan'] = result['tenkan']
        features['ichimoku_kijun'] = result['kijun']
        features['ichimoku_senkou_a'] = result['senkou_a']
        features['ichimoku_senkou_b'] = result['senkou_b']
        
        # Cloud Thickness
        features['ichimoku_cloud_thickness'] = abs(result['senkou_a'] - result['senkou_b'])
        
        # Tenkan/Kijun Cross
        features['ichimoku_tk_cross'] = (result['tenkan'] > result['kijun']).astype(int)
        
        # Price vs Cloud
        cloud_top = result[['senkou_a', 'senkou_b']].max(axis=1)
        cloud_bottom = result[['senkou_a', 'senkou_b']].min(axis=1)
        features['ichimoku_price_vs_cloud'] = ((close > cloud_top).astype(int) - 
                                               (close < cloud_bottom).astype(int))
        
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
