"""369 - Elliott Wave Detector"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ElliottWaveDetector:
    """Elliott Wave Detector - Identifies Elliott Wave patterns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ElliottWaveDetector", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Find swing points
        high_rolling = data['high'].rolling(3, center=True).max()
        low_rolling = data['low'].rolling(3, center=True).min()
        
        peaks = (data['high'] == high_rolling)
        troughs = (data['low'] == low_rolling)
        
        # Elliott Wave structure: 5 waves up (1,2,3,4,5), 3 waves down (A,B,C)
        wave_count = pd.Series(0, index=data.index)
        wave_phase = pd.Series('', index=data.index)
        
        # Simplified wave counting
        for i in range(period, len(data)):
            # Get recent swings
            recent_peaks = peaks.iloc[i-period:i][peaks.iloc[i-period:i]].index
            recent_troughs = troughs.iloc[i-period:i][troughs.iloc[i-period:i]].index
            
            # Count alternating swings
            all_swings = sorted(list(recent_peaks) + list(recent_troughs))
            
            if len(all_swings) >= 5:
                # Check if we have 5-wave structure
                # Wave 1: up, Wave 2: down, Wave 3: up, Wave 4: down, Wave 5: up
                
                wave_count.iloc[i] = len(all_swings) % 8
                
                # Determine phase
                if wave_count.iloc[i] in [1, 3, 5]:
                    wave_phase.iloc[i] = 'impulse'
                elif wave_count.iloc[i] in [2, 4]:
                    wave_phase.iloc[i] = 'correction'
                else:
                    wave_phase.iloc[i] = 'abc'
        
        # Signal: Wave 3 or Wave 5 (strongest impulse waves)
        impulse_signal = (wave_count.isin([3, 5])).astype(float)
        
        # Smooth
        impulse_smooth = impulse_signal.rolling(5).mean()
        
        # Wave strength (based on price momentum)
        momentum = (data['close'] - data['close'].shift(5)) / data['close'].shift(5)
        wave_strength = abs(momentum).fillna(0)
        
        return pd.DataFrame({
            'wave_count': wave_count,
            'wave_phase': wave_phase,
            'impulse_signal': impulse_signal,
            'impulse_smooth': impulse_smooth,
            'wave_strength': wave_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Impulse wave detected
        entries = result['impulse_smooth'] > 0.3
        
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
            'signal_strength': result['wave_strength']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Impulse wave
        entries = result['impulse_signal'] > 0.5
        
        # Exit: Wave complete (correction starts)
        exits = result['wave_count'].diff() != 0
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('wave_complete', index=data.index),
            'signal_strength': result['wave_strength']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['elliott_wave_count'] = result['wave_count']
        features['elliott_impulse_signal'] = result['impulse_signal']
        features['elliott_impulse_smooth'] = result['impulse_smooth']
        features['elliott_wave_strength'] = result['wave_strength']
        features['elliott_impulse_wave'] = (result['wave_count'].isin([3, 5])).astype(int)
        
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

