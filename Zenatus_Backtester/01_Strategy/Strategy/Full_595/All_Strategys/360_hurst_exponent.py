"""360 - Hurst Exponent Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HurstExponent:
    """Hurst Exponent - Measures trend persistence vs mean reversion"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HurstExponent", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Calculate Hurst exponent using R/S analysis
        hurst = pd.Series(0.5, index=data.index)
        
        for i in range(period, len(data)):
            window = data['close'].iloc[i-period:i]
            
            if len(window) > 2:
                # Mean-adjusted series
                mean_adj = window - window.mean()
                
                # Cumulative sum
                cumsum = mean_adj.cumsum()
                
                # Range
                R = cumsum.max() - cumsum.min()
                
                # Standard deviation
                S = window.std()
                
                # R/S ratio
                if S > 0:
                    RS = R / S
                    
                    # Hurst exponent: R/S ~ n^H
                    # H = log(R/S) / log(n)
                    if RS > 0:
                        H = np.log(RS) / np.log(period)
                        hurst.iloc[i] = H
        
        # Clip to valid range
        hurst = hurst.clip(0, 1)
        
        # Interpretation:
        # H < 0.5: Mean reverting
        # H = 0.5: Random walk
        # H > 0.5: Trending
        
        # Market regime
        regime = pd.Series('random', index=data.index)
        regime[hurst < 0.45] = 'mean_reverting'
        regime[hurst > 0.55] = 'trending'
        
        # Signal based on regime
        # Trending: follow trend
        # Mean reverting: fade extremes
        
        sma = data['close'].rolling(period).mean()
        
        signal = pd.Series(0.5, index=data.index)
        
        # Trending regime: trend following
        trending_mask = hurst > 0.55
        signal[trending_mask] = (data['close'][trending_mask] > sma[trending_mask]).astype(float)
        
        # Mean reverting regime: contrarian
        reverting_mask = hurst < 0.45
        signal[reverting_mask] = (data['close'][reverting_mask] < sma[reverting_mask]).astype(float)
        
        # Smooth
        signal_smooth = signal.rolling(5).mean()
        
        return pd.DataFrame({
            'hurst': hurst,
            'regime': regime,
            'signal': signal,
            'signal_smooth': signal_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong signal
        entries = result['signal_smooth'] > 0.6
        
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
            'signal_strength': abs(result['hurst'] - 0.5) * 2
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong signal
        entries = result['signal_smooth'] > 0.6
        
        # Exit: Weak signal or regime change
        exits = (result['signal_smooth'] < 0.4)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('hurst_reversal', index=data.index),
            'signal_strength': abs(result['hurst'] - 0.5) * 2
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['hurst_exponent'] = result['hurst']
        features['hurst_signal'] = result['signal']
        features['hurst_smooth'] = result['signal_smooth']
        features['hurst_trending'] = (result['hurst'] > 0.55).astype(int)
        features['hurst_reverting'] = (result['hurst'] < 0.45).astype(int)
        features['hurst_random'] = ((result['hurst'] >= 0.45) & (result['hurst'] <= 0.55)).astype(int)
        
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

