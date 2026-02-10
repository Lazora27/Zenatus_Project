"""304 - Regime Switching Model"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RegimeSwitching:
    """Regime Switching - Detects market regime changes (trending vs ranging)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RegimeSwitching", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate returns
        returns = data['close'].pct_change()
        
        # Volatility
        volatility = returns.rolling(period).std()
        
        # Trend strength (ADX-like)
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        plus_dm = data['high'] - data['high'].shift(1)
        minus_dm = data['low'].shift(1) - data['low']
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr_smooth = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / tr_smooth)
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr_smooth)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(period).mean()
        
        # Regime classification
        # Trending: High ADX (>25), Low volatility relative to trend
        # Ranging: Low ADX (<20), High volatility relative to trend
        
        regime = pd.Series(0, index=data.index)  # 0=Ranging, 1=Trending
        regime[adx > 25] = 1
        
        # Regime confidence
        regime_confidence = adx / 50  # Normalize to 0-1
        
        # Regime changes
        regime_change = regime.diff()
        
        return pd.DataFrame({
            'regime': regime,
            'adx': adx,
            'volatility': volatility,
            'regime_confidence': regime_confidence,
            'regime_change': regime_change,
            'trending': (regime == 1).astype(int),
            'ranging': (regime == 0).astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Regime switches to trending
        entries = (result['regime_change'] == 1)
        
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
            'signal_strength': result['regime_confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Regime switches to trending
        entries = result['regime_change'] == 1
        
        # Exit: Regime switches to ranging
        exits = result['regime_change'] == -1
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('regime_change', index=data.index),
            'signal_strength': result['regime_confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['regime'] = result['regime']
        features['adx'] = result['adx']
        features['volatility'] = result['volatility']
        features['regime_confidence'] = result['regime_confidence']
        features['trending'] = result['trending']
        features['ranging'] = result['ranging']
        features['regime_change'] = result['regime_change']
        features['strong_trend'] = (result['adx'] > 30).astype(int)
        
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

