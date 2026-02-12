"""349 - Wavelet Decomposition Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_WaveletDecomposition:
    """Wavelet Decomposition - Multi-scale time-frequency analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_levels': {'default': 3, 'values': [2,3,4], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "WaveletDecomposition", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_levels = params.get('n_levels', 3)
        
        # Simplified wavelet decomposition (Haar wavelet)
        price = data['close']
        
        # Decompose into approximation and detail coefficients
        approximations = []
        details = []
        
        current = price.copy()
        
        for level in range(min(n_levels, 3)):
            # Approximation (low-pass filter)
            approx = current.rolling(2).mean()
            
            # Detail (high-pass filter)
            detail = current - approx
            
            approximations.append(approx)
            details.append(detail)
            
            # Downsample for next level
            current = approx
        
        # Reconstruct signal from components
        # Use approximation (trend) and details (noise/patterns)
        
        # Trend component (last approximation)
        trend_component = approximations[-1]
        
        # Pattern component (sum of details)
        pattern_component = sum(details) / len(details)
        
        # Signal: trend + significant patterns
        trend_signal = (trend_component > trend_component.shift(1)).astype(float)
        pattern_signal = (pattern_component > pattern_component.rolling(5).mean()).astype(float)
        
        # Combined wavelet signal
        wavelet_signal = (trend_signal + pattern_signal) / 2
        
        # Smooth
        wavelet_smooth = wavelet_signal.rolling(5).mean()
        
        # Energy in each level
        energy_levels = [abs(d).rolling(period).mean() for d in details]
        total_energy = sum(energy_levels)
        
        return pd.DataFrame({
            'trend_component': trend_component,
            'pattern_component': pattern_component,
            'wavelet_signal': wavelet_signal,
            'wavelet_smooth': wavelet_smooth,
            'total_energy': total_energy
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong wavelet signal
        entries = result['wavelet_smooth'] > 0.6
        
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
            'signal_strength': result['wavelet_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong signal
        entries = result['wavelet_smooth'] > 0.6
        
        # Exit: Weak signal
        exits = result['wavelet_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('wavelet_reversal', index=data.index),
            'signal_strength': result['wavelet_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['wavelet_trend'] = result['trend_component']
        features['wavelet_pattern'] = result['pattern_component']
        features['wavelet_signal'] = result['wavelet_signal']
        features['wavelet_smooth'] = result['wavelet_smooth']
        features['wavelet_energy'] = result['total_energy']
        features['wavelet_strong'] = (result['wavelet_smooth'] > 0.6).astype(int)
        
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

