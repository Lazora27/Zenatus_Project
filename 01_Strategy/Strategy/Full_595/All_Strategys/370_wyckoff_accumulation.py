"""370 - Wyckoff Accumulation/Distribution"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_WyckoffAccumulation:
    """Wyckoff Accumulation - Detects accumulation and distribution phases"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "WyckoffAccumulation", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Wyckoff principles
        # 1. Price-Volume relationship
        # 2. Support/Resistance
        # 3. Effort vs Result
        
        # Price change
        price_change = data['close'].pct_change().fillna(0)
        
        # Volume change
        volume_change = data['volume'].pct_change().fillna(0)
        
        # Effort (volume) vs Result (price change)
        effort_result = pd.Series(0.0, index=data.index)
        
        for i in range(1, len(data)):
            # High volume, small price change = accumulation/distribution
            # Low volume, large price change = markup/markdown
            
            vol_percentile = (data['volume'].iloc[i] - data['volume'].iloc[i-period:i].min()) / (
                data['volume'].iloc[i-period:i].max() - data['volume'].iloc[i-period:i].min() + 1e-10
            )
            
            price_percentile = abs(price_change.iloc[i]) / (abs(price_change.iloc[i-period:i]).max() + 1e-10)
            
            # Accumulation: high volume, low price change, price near support
            if vol_percentile > 0.7 and price_percentile < 0.3:
                effort_result.iloc[i] = 1  # Accumulation
            # Distribution: high volume, low price change, price near resistance
            elif vol_percentile > 0.7 and price_percentile < 0.3 and price_change.iloc[i] < 0:
                effort_result.iloc[i] = -1  # Distribution
            else:
                effort_result.iloc[i] = 0
        
        # Support/Resistance levels
        support = data['low'].rolling(period).min()
        resistance = data['high'].rolling(period).max()
        
        # Position in range
        range_position = (data['close'] - support) / (resistance - support + 1e-10)
        
        # Accumulation phase: low in range + high volume
        accumulation_phase = ((range_position < 0.3) & (effort_result == 1)).astype(int)
        
        # Spring (false breakdown before markup)
        spring = ((data['low'] < support) & (data['close'] > support)).astype(int)
        
        # Wyckoff signal
        wyckoff_signal = (accumulation_phase | spring).astype(float)
        
        # Smooth
        wyckoff_smooth = wyckoff_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'effort_result': effort_result,
            'range_position': range_position,
            'accumulation_phase': accumulation_phase,
            'spring': spring,
            'wyckoff_signal': wyckoff_signal,
            'wyckoff_smooth': wyckoff_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Accumulation or spring detected
        entries = result['wyckoff_smooth'] > 0.3
        
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
            'signal_strength': result['wyckoff_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Accumulation
        entries = result['accumulation_phase'] == 1
        
        # Exit: Distribution or high in range
        exits = (result['effort_result'] == -1) | (result['range_position'] > 0.8)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('wyckoff_distribution', index=data.index),
            'signal_strength': result['wyckoff_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['wyckoff_effort_result'] = result['effort_result']
        features['wyckoff_range_position'] = result['range_position']
        features['wyckoff_accumulation'] = result['accumulation_phase']
        features['wyckoff_spring'] = result['spring']
        features['wyckoff_signal'] = result['wyckoff_signal']
        features['wyckoff_smooth'] = result['wyckoff_smooth']
        features['wyckoff_phase_detected'] = (result['wyckoff_signal'] > 0.3).astype(int)
        
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

