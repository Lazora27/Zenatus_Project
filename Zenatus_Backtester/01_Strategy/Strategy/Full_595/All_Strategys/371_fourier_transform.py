"""371 - Fourier Transform Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FourierTransform:
    """Fourier Transform - Frequency domain analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FourierTransform", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Detrend price
        price = data['close']
        trend = price.rolling(period).mean()
        detrended = price - trend
        
        # FFT analysis
        fft_magnitude = pd.Series(0.0, index=data.index)
        dominant_frequency = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = detrended.iloc[i-period:i].fillna(0).values
            
            # Fast Fourier Transform
            fft = np.fft.fft(window)
            
            # Magnitude spectrum
            magnitude = np.abs(fft)
            
            # Find dominant frequency (excluding DC component)
            if len(magnitude) > 1:
                dominant_idx = np.argmax(magnitude[1:len(magnitude)//2]) + 1
                dominant_frequency.iloc[i] = dominant_idx
                fft_magnitude.iloc[i] = magnitude[dominant_idx]
        
        # Reconstruct signal using dominant frequency
        reconstructed = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            if dominant_frequency.iloc[i] > 0:
                # Simple sinusoidal reconstruction
                freq = dominant_frequency.iloc[i] / period
                phase = i * 2 * np.pi * freq
                reconstructed.iloc[i] = fft_magnitude.iloc[i] * np.cos(phase)
        
        # Signal: phase of dominant cycle
        cycle_phase = (reconstructed > 0).astype(float)
        
        # Smooth
        cycle_smooth = cycle_phase.rolling(5).mean()
        
        # Cycle strength
        cycle_strength = fft_magnitude / (fft_magnitude.rolling(period).max() + 1e-10)
        
        return pd.DataFrame({
            'fft_magnitude': fft_magnitude,
            'dominant_frequency': dominant_frequency,
            'reconstructed': reconstructed,
            'cycle_phase': cycle_phase,
            'cycle_smooth': cycle_smooth,
            'cycle_strength': cycle_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive cycle phase
        entries = result['cycle_smooth'] > 0.6
        
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
            'signal_strength': result['cycle_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive phase
        entries = result['cycle_phase'] > 0.5
        
        # Exit: Negative phase
        exits = result['cycle_phase'] < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('cycle_reversal', index=data.index),
            'signal_strength': result['cycle_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['fft_magnitude'] = result['fft_magnitude']
        features['fft_dominant_freq'] = result['dominant_frequency']
        features['fft_reconstructed'] = result['reconstructed']
        features['fft_cycle_phase'] = result['cycle_phase']
        features['fft_cycle_smooth'] = result['cycle_smooth']
        features['fft_cycle_strength'] = result['cycle_strength']
        features['fft_positive_phase'] = (result['cycle_phase'] > 0.5).astype(int)
        
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

