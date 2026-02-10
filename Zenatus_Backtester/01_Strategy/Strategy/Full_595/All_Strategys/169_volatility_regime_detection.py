"""169 - Volatility Regime Detection"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolatilityRegimeDetection:
    """Volatility Regime Detection - Identifies High/Low Volatility Regimes"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 1.5, 'values': [1.0,1.2,1.5,1.8,2.0,2.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolatilityRegimeDetection", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 1.5)
        
        # Calculate volatility (ATR-based)
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift(1))
        low_close = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # Volatility percentile
        vol_percentile = atr.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x) if len(x) > 0 else 0.5)
        
        # Regime detection (0=Low, 1=Normal, 2=High)
        vol_ma = atr.rolling(period*2).mean()
        vol_std = atr.rolling(period*2).std()
        
        regime = pd.Series(1, index=data.index)  # Default: Normal
        regime[atr > vol_ma + threshold * vol_std] = 2  # High volatility
        regime[atr < vol_ma - threshold * vol_std] = 0  # Low volatility
        
        # Regime changes
        regime_change = regime.diff().fillna(0)
        
        return pd.DataFrame({
            'atr': atr,
            'vol_percentile': vol_percentile,
            'regime': regime,
            'regime_change': regime_change,
            'vol_ma': vol_ma,
            'vol_std': vol_std
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Regime change to high volatility
        entries = (result['regime_change'] > 0) & (result['regime'] == 2)
        
        # Manual TP/SL
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price = 0
        
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
            'signal_strength': result['vol_percentile']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Regime change to high volatility
        entries = (result['regime_change'] > 0) & (result['regime'] == 2)
        
        # Exit: Regime change back to normal/low
        exits = (result['regime_change'] < 0) & (result['regime'] <= 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('regime_change', index=data.index),
            'signal_strength': result['vol_percentile']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['vol_regime'] = result['regime']
        features['vol_percentile'] = result['vol_percentile']
        features['vol_regime_change'] = result['regime_change']
        features['atr_normalized'] = result['atr'] / data['close']
        features['vol_ma_ratio'] = result['atr'] / (result['vol_ma'] + 1e-10)
        features['vol_zscore'] = (result['atr'] - result['vol_ma']) / (result['vol_std'] + 1e-10)
        features['high_vol_regime'] = (result['regime'] == 2).astype(int)
        features['low_vol_regime'] = (result['regime'] == 0).astype(int)
        
        return features
    
    def validate_params(self, params):
        for key, value in params.items():
            if key in self.PARAMETERS:
                param_info = self.PARAMETERS[key]
                if 'min' in param_info and value < param_info['min']:
                    raise ValueError(f"{key} must be >= {param_info['min']}")
                if 'max' in param_info and value > param_info['max']:
                    raise ValueError(f"{key} must be <= {param_info['max']}")
