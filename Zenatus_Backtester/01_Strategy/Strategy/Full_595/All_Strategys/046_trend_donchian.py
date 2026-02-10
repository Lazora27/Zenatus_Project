"""
046 - Donchian Channels
Klassische Breakout-Channels basierend auf High/Low
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


class Indicator_DonchianChannels:
    """
    Donchian Channels - Breakout/Trend
    
    Beschreibung:
        Channels basierend auf höchstem High und niedrigstem Low.
        Upper Channel = Highest High(period)
        Lower Channel = Lowest Low(period)
        Middle Channel = (Upper + Lower) / 2
    
    Parameters:
        - period: Lookback-Periode (5-100)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei Channel Breakout, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei Breakout, Exit bei Reverse Breakout
    """
    
    PARAMETERS = {
        'period': {
            'default': 20,
            'min': 5,
            'max': 100,
            'values': [5,7,8,11,13,14,17,19,20,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'optimize': True,
            'ml_feature': True,
            'description': 'Donchian lookback period'
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
        self.name = "DonchianChannels"
        self.category = "Breakout"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Berechnet Donchian Channels.
        
        Formula:
            Upper = Highest High(period)
            Lower = Lowest Low(period)
            Middle = (Upper + Lower) / 2
        
        Args:
            data: OHLCV DataFrame
            params: {'period': int}
            
        Returns:
            pd.DataFrame: upper, middle, lower, channel_width
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Upper and Lower Channels
        upper = high.rolling(window=period, min_periods=1).max()
        lower = low.rolling(window=period, min_periods=1).min()
        
        # Middle Channel
        middle = (upper + lower) / 2
        
        # Channel Width
        channel_width = (upper - lower) / (middle + 1e-10)
        
        return pd.DataFrame({
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'channel_width': channel_width
        }, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie mit MANUELLER Exit-Logik
        
        Entry: Price breaks above Upper Channel
        Exit: Manual TP/SL
        """
        result = self.calculate(data, params)
        close = data['close']
        
        # Entry bei Breakout über Upper Channel
        entries = (close > result['upper'].shift(1))
        
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
        position_in_channel = (close - result['lower']) / (result['upper'] - result['lower'] + 1e-10)
        signal_strength = position_in_channel.clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie - Donchian-basiert
        
        Entry: Price breaks above Upper Channel
        Exit: Price breaks below Lower Channel
        """
        result = self.calculate(data, params)
        close = data['close']
        
        # Entry bei Breakout über Upper Channel
        entries = (close > result['upper'].shift(1))
        
        # Exit bei Breakout unter Lower Channel
        exits = (close < result['lower'].shift(1))
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'donchian_lower_breakout'
        
        position_in_channel = (close - result['lower']) / (result['upper'] - result['lower'] + 1e-10)
        signal_strength = position_in_channel.clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus Donchian Channels.
        
        Returns:
            DataFrame mit Features:
            - dc_upper: Upper Channel
            - dc_middle: Middle Channel
            - dc_lower: Lower Channel
            - dc_width: Channel Width
            - dc_position: Position im Channel
            - dc_breakout_up: Breakout nach oben
            - dc_breakout_down: Breakout nach unten
        """
        result = self.calculate(data, params)
        close = data['close']
        
        features = pd.DataFrame(index=data.index)
        features['dc_upper'] = result['upper']
        features['dc_middle'] = result['middle']
        features['dc_lower'] = result['lower']
        features['dc_width'] = result['channel_width']
        
        # Position im Channel (0 = lower, 1 = upper)
        features['dc_position'] = (close - result['lower']) / (result['upper'] - result['lower'] + 1e-10)
        
        # Breakout Detection
        features['dc_breakout_up'] = (close > result['upper'].shift(1)).astype(int)
        features['dc_breakout_down'] = (close < result['lower'].shift(1)).astype(int)
        
        # Distance from channels
        features['dc_distance_upper'] = (result['upper'] - close) / close
        features['dc_distance_lower'] = (close - result['lower']) / close
        
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
