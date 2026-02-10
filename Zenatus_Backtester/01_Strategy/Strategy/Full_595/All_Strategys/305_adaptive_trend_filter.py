"""305 - Adaptive Trend Filter"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AdaptiveTrendFilter:
    """Adaptive Trend Filter - Adjusts to market conditions automatically"""
    PARAMETERS = {
        'min_period': {'default': 5, 'values': [3,5,7,8], 'optimize': True},
        'max_period': {'default': 50, 'values': [30,40,50,60,70], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AdaptiveTrendFilter", "Trend", __version__
    
    def calculate(self, data, params):
        min_period = params.get('min_period', 5)
        max_period = params.get('max_period', 50)
        
        # Calculate volatility for adaptation
        returns = data['close'].pct_change()
        volatility = returns.rolling(20).std()
        
        # Adaptive period based on volatility
        vol_percentile = volatility.rolling(100).apply(
            lambda x: pd.Series(x).rank().iloc[-1] / len(x) if len(x) > 0 else 0.5
        )
        
        # Fill NaN
        vol_percentile = vol_percentile.fillna(0.5)
        
        # High volatility = shorter period, Low volatility = longer period
        adaptive_period = (min_period + (max_period - min_period) * (1 - vol_percentile))
        adaptive_period = adaptive_period.fillna(min_period).clip(min_period, max_period).astype(int)
        
        # Calculate adaptive moving average
        adaptive_ma = pd.Series(index=data.index, dtype=float)
        
        for i in range(max_period, len(data)):
            period = int(adaptive_period.iloc[i])
            if period > 0:
                adaptive_ma.iloc[i] = data['close'].iloc[i-period:i].mean()
        
        # Trend direction
        trend_up = data['close'] > adaptive_ma
        trend_down = data['close'] < adaptive_ma
        
        # Trend strength
        distance = abs(data['close'] - adaptive_ma) / adaptive_ma * 100
        
        return pd.DataFrame({
            'adaptive_ma': adaptive_ma,
            'adaptive_period': adaptive_period,
            'trend_up': trend_up.astype(int),
            'trend_down': trend_down.astype(int),
            'distance': distance,
            'volatility': volatility
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above adaptive MA
        entries = (data['close'] > result['adaptive_ma']) & (data['close'].shift(1) <= result['adaptive_ma'].shift(1))
        
        # Manual TP/SL
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        
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
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': result['distance'] / 10
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Price crosses above adaptive MA
        entries = (data['close'] > result['adaptive_ma']) & (data['close'].shift(1) <= result['adaptive_ma'].shift(1))
        
        # Exit: Price crosses below adaptive MA
        exits = (data['close'] < result['adaptive_ma']) & (data['close'].shift(1) >= result['adaptive_ma'].shift(1))
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('adaptive_ma_cross', index=data.index),
            'signal_strength': result['distance'] / 10
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['adaptive_ma'] = result['adaptive_ma']
        features['adaptive_period'] = result['adaptive_period']
        features['trend_up'] = result['trend_up']
        features['trend_down'] = result['trend_down']
        features['distance'] = result['distance']
        features['volatility'] = result['volatility']
        features['above_adaptive_ma'] = (data['close'] > result['adaptive_ma']).astype(int)
        features['period_short'] = (result['adaptive_period'] < 20).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass

    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100, 150],
            'sl_pips': [15, 25, 35, 50, 75]
        }

