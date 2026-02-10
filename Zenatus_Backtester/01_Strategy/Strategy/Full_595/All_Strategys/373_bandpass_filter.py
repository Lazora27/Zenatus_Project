"""373 - Bandpass Filter Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BandpassFilter:
    """Bandpass Filter - Isolates specific frequency bands"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'low_freq': {'default': 5, 'values': [3,5,7,10], 'optimize': False},
        'high_freq': {'default': 15, 'values': [10,15,20,25], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BandpassFilter", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        low_freq = params.get('low_freq', 5)
        high_freq = params.get('high_freq', 15)
        
        # Detrend
        price = data['close']
        trend = price.rolling(period).mean()
        detrended = price - trend
        
        # Bandpass filter using FFT
        filtered_signal = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            window = detrended.iloc[i-period:i].fillna(0).values
            
            # FFT
            fft = np.fft.fft(window)
            
            # Create bandpass filter
            bandpass = np.zeros_like(fft)
            
            # Keep only frequencies in band
            bandpass[low_freq:high_freq] = fft[low_freq:high_freq]
            bandpass[-high_freq:-low_freq] = fft[-high_freq:-low_freq]
            
            # Inverse FFT
            filtered = np.fft.ifft(bandpass)
            
            # Take real part
            filtered_signal.iloc[i] = np.real(filtered[-1])
        
        # Signal: positive filtered value
        bandpass_signal = (filtered_signal > 0).astype(float)
        
        # Smooth
        bandpass_smooth = bandpass_signal.rolling(5).mean()
        
        # Filter strength
        filter_strength = abs(filtered_signal) / (abs(filtered_signal).rolling(period).max() + 1e-10)
        
        return pd.DataFrame({
            'filtered_signal': filtered_signal,
            'bandpass_signal': bandpass_signal,
            'bandpass_smooth': bandpass_smooth,
            'filter_strength': filter_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive filtered signal
        entries = result['bandpass_smooth'] > 0.6
        
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
            'signal_strength': result['filter_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Positive signal
        entries = result['bandpass_signal'] > 0.5
        
        # Exit: Negative signal
        exits = result['bandpass_signal'] < 0.5
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('bandpass_reversal', index=data.index),
            'signal_strength': result['filter_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['bandpass_filtered'] = result['filtered_signal']
        features['bandpass_signal'] = result['bandpass_signal']
        features['bandpass_smooth'] = result['bandpass_smooth']
        features['bandpass_strength'] = result['filter_strength']
        features['bandpass_positive'] = (result['bandpass_signal'] > 0.5).astype(int)
        
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

