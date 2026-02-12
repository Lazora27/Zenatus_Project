"""356 - Cointegration Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CointegrationSignal:
    """Cointegration Signal - Mean reversion based on cointegration"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CointegrationSignal", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Use price and its moving average as "cointegrated" series
        price = data['close']
        sma = price.rolling(period).mean()
        
        # Spread (residual from cointegration)
        spread = price - sma
        
        # Spread statistics
        spread_mean = spread.rolling(period).mean()
        spread_std = spread.rolling(period).std()
        
        # Z-score
        zscore = (spread - spread_mean) / (spread_std + 1e-10)
        
        # Mean reversion signal
        # Buy when spread is low (price below MA)
        # Sell when spread is high (price above MA)
        
        # Cointegration strength (stationarity test)
        # ADF-like: check if spread reverts to mean
        spread_autocorr = spread.rolling(period).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0
        )
        
        # Strong mean reversion = high cointegration
        cointegration_strength = 1 - abs(spread_autocorr)
        
        # Signal: mean reversion opportunity
        reversion_signal = (-zscore + 1) / 2  # Normalize to 0-1
        reversion_signal = reversion_signal.clip(0, 1)
        
        # Smooth
        reversion_smooth = reversion_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'spread': spread,
            'zscore': zscore,
            'cointegration_strength': cointegration_strength,
            'reversion_signal': reversion_signal,
            'reversion_smooth': reversion_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong mean reversion opportunity
        entries = (result['reversion_smooth'] > 0.6) & (result['cointegration_strength'] > 0.5)
        
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
            'signal_strength': result['cointegration_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Spread extreme (mean reversion)
        entries = abs(result['zscore']) > 1.5
        
        # Exit: Spread normalized
        exits = abs(result['zscore']) < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('spread_normalized', index=data.index),
            'signal_strength': result['cointegration_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['coint_spread'] = result['spread']
        features['coint_zscore'] = result['zscore']
        features['coint_strength'] = result['cointegration_strength']
        features['coint_reversion'] = result['reversion_signal']
        features['coint_smooth'] = result['reversion_smooth']
        features['coint_extreme_spread'] = (abs(result['zscore']) > 1.5).astype(int)
        
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

