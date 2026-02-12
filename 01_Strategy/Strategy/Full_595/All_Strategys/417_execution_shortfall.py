"""417 - Execution Shortfall"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ExecutionShortfall:
    """Execution Shortfall - Implementation shortfall cost"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ExecutionShortfall", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Decision price (open)
        decision_price = data['open']
        
        # Execution price (close)
        execution_price = data['close']
        
        # Shortfall = execution - decision
        shortfall = execution_price - decision_price
        
        # Relative shortfall
        relative_shortfall = shortfall / decision_price
        
        # Average shortfall
        avg_shortfall = relative_shortfall.rolling(period).mean()
        
        # Shortfall volatility
        shortfall_volatility = relative_shortfall.rolling(period).std()
        
        # Execution quality (low shortfall = good)
        execution_quality = 1 / (abs(avg_shortfall) + 1e-10)
        quality_normalized = execution_quality / execution_quality.rolling(50).max()
        
        # Shortfall trend
        shortfall_trend = avg_shortfall.diff()
        
        # Smooth
        quality_smooth = quality_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'shortfall': shortfall,
            'relative_shortfall': relative_shortfall,
            'avg_shortfall': avg_shortfall,
            'shortfall_volatility': shortfall_volatility,
            'execution_quality': quality_normalized,
            'shortfall_trend': shortfall_trend,
            'quality_smooth': quality_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High execution quality
        entries = result['quality_smooth'] > 0.6
        
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
            'signal_strength': result['quality_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Good quality
        entries = result['execution_quality'] > 0.6
        
        # Exit: Poor quality
        exits = result['execution_quality'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('poor_execution', index=data.index),
            'signal_strength': result['quality_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['exec_shortfall'] = result['shortfall']
        features['exec_shortfall_relative'] = result['relative_shortfall']
        features['exec_shortfall_avg'] = result['avg_shortfall']
        features['exec_shortfall_volatility'] = result['shortfall_volatility']
        features['exec_quality'] = result['execution_quality']
        features['exec_shortfall_trend'] = result['shortfall_trend']
        features['exec_quality_smooth'] = result['quality_smooth']
        features['exec_high_quality'] = (result['execution_quality'] > 0.6).astype(int)
        
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

