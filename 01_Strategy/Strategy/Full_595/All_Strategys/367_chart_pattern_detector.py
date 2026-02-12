"""367 - Chart Pattern Detector"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ChartPatternDetector:
    """Chart Pattern Detector - Detects head & shoulders, triangles, flags, etc."""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ChartPatternDetector", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Identify local peaks and troughs
        high_rolling = data['high'].rolling(5, center=True).max()
        low_rolling = data['low'].rolling(5, center=True).min()
        
        is_peak = (data['high'] == high_rolling).astype(int)
        is_trough = (data['low'] == low_rolling).astype(int)
        
        # Pattern 1: Double Top/Bottom
        double_top = pd.Series(0, index=data.index)
        double_bottom = pd.Series(0, index=data.index)
        
        for i in range(period, len(data)):
            peaks = is_peak.iloc[i-period:i]
            troughs = is_trough.iloc[i-period:i]
            
            peak_indices = peaks[peaks == 1].index
            trough_indices = troughs[troughs == 1].index
            
            # Double top: two similar peaks
            if len(peak_indices) >= 2:
                last_two_peaks = data['high'].loc[peak_indices[-2:]]
                if abs(last_two_peaks.iloc[0] - last_two_peaks.iloc[1]) / last_two_peaks.mean() < 0.02:
                    double_top.iloc[i] = 1
            
            # Double bottom: two similar troughs
            if len(trough_indices) >= 2:
                last_two_troughs = data['low'].loc[trough_indices[-2:]]
                if abs(last_two_troughs.iloc[0] - last_two_troughs.iloc[1]) / last_two_troughs.mean() < 0.02:
                    double_bottom.iloc[i] = 1
        
        # Pattern 2: Triangle (converging highs and lows)
        triangle = pd.Series(0, index=data.index)
        
        for i in range(period, len(data)):
            highs = data['high'].iloc[i-period:i]
            lows = data['low'].iloc[i-period:i]
            
            # Linear regression on highs and lows
            x = np.arange(len(highs))
            
            # High trend
            high_slope = np.polyfit(x, highs, 1)[0] if len(highs) > 1 else 0
            
            # Low trend
            low_slope = np.polyfit(x, lows, 1)[0] if len(lows) > 1 else 0
            
            # Converging if slopes opposite and similar magnitude
            if high_slope < 0 and low_slope > 0:
                if abs(high_slope + low_slope) < abs(high_slope) * 0.5:
                    triangle.iloc[i] = 1
        
        # Pattern 3: Flag (consolidation after strong move)
        flag = pd.Series(0, index=data.index)
        
        for i in range(period, len(data)):
            # Strong move
            price_change = (data['close'].iloc[i] - data['close'].iloc[i-10]) / data['close'].iloc[i-10]
            
            # Consolidation (low volatility)
            recent_vol = data['close'].iloc[i-5:i].std()
            avg_vol = data['close'].iloc[i-period:i].std()
            
            if abs(price_change) > 0.02 and recent_vol < avg_vol * 0.5:
                flag.iloc[i] = 1
        
        # Combined pattern score
        pattern_score = (double_bottom * 0.4 + triangle * 0.3 + flag * 0.3)
        
        # Smooth
        pattern_smooth = pattern_score.rolling(5).mean()
        
        return pd.DataFrame({
            'double_top': double_top,
            'double_bottom': double_bottom,
            'triangle': triangle,
            'flag': flag,
            'pattern_score': pattern_score,
            'pattern_smooth': pattern_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Bullish pattern detected
        entries = result['pattern_smooth'] > 0.3
        
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
            'signal_strength': result['pattern_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Pattern detected
        entries = result['pattern_score'] > 0.3
        
        # Exit: Pattern completed (5 bars later)
        exits = result['pattern_score'].shift(5) > 0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pattern_complete', index=data.index),
            'signal_strength': result['pattern_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['chart_double_top'] = result['double_top']
        features['chart_double_bottom'] = result['double_bottom']
        features['chart_triangle'] = result['triangle']
        features['chart_flag'] = result['flag']
        features['chart_pattern_score'] = result['pattern_score']
        features['chart_pattern_smooth'] = result['pattern_smooth']
        features['chart_pattern_detected'] = (result['pattern_score'] > 0.3).astype(int)
        
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

