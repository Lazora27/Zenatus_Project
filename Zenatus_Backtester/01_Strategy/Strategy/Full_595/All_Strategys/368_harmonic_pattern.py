"""368 - Harmonic Pattern Recognition"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HarmonicPattern:
    """Harmonic Pattern - Fibonacci-based harmonic patterns (Gartley, Butterfly, etc.)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HarmonicPattern", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Fibonacci ratios
        fib_618 = 0.618
        fib_786 = 0.786
        fib_886 = 0.886
        fib_1272 = 1.272
        
        # Find swing points (XABCD pattern)
        high_rolling = data['high'].rolling(5, center=True).max()
        low_rolling = data['low'].rolling(5, center=True).min()
        
        peaks = (data['high'] == high_rolling)
        troughs = (data['low'] == low_rolling)
        
        # Harmonic pattern detection
        gartley_pattern = pd.Series(0, index=data.index)
        butterfly_pattern = pd.Series(0, index=data.index)
        
        for i in range(period, len(data)):
            # Get last 5 swing points
            peak_indices = peaks.iloc[i-period:i][peaks.iloc[i-period:i]].index
            trough_indices = troughs.iloc[i-period:i][troughs.iloc[i-period:i]].index
            
            if len(peak_indices) >= 2 and len(trough_indices) >= 2:
                # Simplified: check ratios
                try:
                    X = data['low'].iloc[i-period]
                    A = data['high'].iloc[i-int(period*0.7)]
                    B = data['low'].iloc[i-int(period*0.5)]
                    C = data['high'].iloc[i-int(period*0.3)]
                    D = data['close'].iloc[i]
                    
                    # XA leg
                    XA = A - X
                    
                    # AB retracement
                    AB = A - B
                    ab_ratio = AB / XA if XA != 0 else 0
                    
                    # BC retracement
                    BC = C - B
                    bc_ratio = BC / AB if AB != 0 else 0
                    
                    # Gartley: AB=0.618*XA, BC=0.382-0.886*AB
                    if abs(ab_ratio - fib_618) < 0.1:
                        gartley_pattern.iloc[i] = 1
                    
                    # Butterfly: AB=0.786*XA
                    if abs(ab_ratio - fib_786) < 0.1:
                        butterfly_pattern.iloc[i] = 1
                        
                except:
                    pass
        
        # Combined harmonic score
        harmonic_score = (gartley_pattern * 0.6 + butterfly_pattern * 0.4)
        
        # Smooth
        harmonic_smooth = harmonic_score.rolling(5).mean()
        
        return pd.DataFrame({
            'gartley': gartley_pattern,
            'butterfly': butterfly_pattern,
            'harmonic_score': harmonic_score,
            'harmonic_smooth': harmonic_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Harmonic pattern detected
        entries = result['harmonic_smooth'] > 0.3
        
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
            'signal_strength': result['harmonic_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Pattern detected
        entries = result['harmonic_score'] > 0.3
        
        # Exit: Pattern completed
        exits = result['harmonic_score'].shift(10) > 0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('harmonic_complete', index=data.index),
            'signal_strength': result['harmonic_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['harmonic_gartley'] = result['gartley']
        features['harmonic_butterfly'] = result['butterfly']
        features['harmonic_score'] = result['harmonic_score']
        features['harmonic_smooth'] = result['harmonic_smooth']
        features['harmonic_detected'] = (result['harmonic_score'] > 0.3).astype(int)
        
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

