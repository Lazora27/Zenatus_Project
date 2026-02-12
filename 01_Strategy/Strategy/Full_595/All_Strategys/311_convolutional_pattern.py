"""311 - Convolutional Pattern Detection"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ConvolutionalPattern:
    """Convolutional Pattern - CNN-inspired pattern detection"""
    PARAMETERS = {
        'kernel_size': {'default': 5, 'values': [3,5,7,8,11], 'optimize': True},
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ConvolutionalPattern", "Statistics", __version__
    
    def calculate(self, data, params):
        kernel_size = params.get('kernel_size', 5)
        period = params.get('period', 20)
        
        # Normalize price
        price_norm = (data['close'] - data['close'].rolling(period).min()) / (
            data['close'].rolling(period).max() - data['close'].rolling(period).min() + 1e-10
        )
        
        # Convolutional filters (simplified CNN)
        # Filter 1: Uptrend detector
        uptrend_kernel = np.linspace(-1, 1, kernel_size)
        conv_uptrend = price_norm.rolling(kernel_size).apply(
            lambda x: np.corrcoef(x, uptrend_kernel)[0, 1] if len(x) == kernel_size else 0,
            raw=True
        )
        
        # Filter 2: Downtrend detector
        downtrend_kernel = np.linspace(1, -1, kernel_size)
        conv_downtrend = price_norm.rolling(kernel_size).apply(
            lambda x: np.corrcoef(x, downtrend_kernel)[0, 1] if len(x) == kernel_size else 0,
            raw=True
        )
        
        # Filter 3: Volatility detector
        conv_volatility = price_norm.rolling(kernel_size).std()
        
        # Pooling layer (max pooling)
        pool_size = 3
        conv_uptrend_pooled = conv_uptrend.rolling(pool_size).max()
        conv_downtrend_pooled = conv_downtrend.rolling(pool_size).max()
        
        # Pattern score
        pattern_score = (conv_uptrend_pooled - conv_downtrend_pooled + 1) / 2
        pattern_score = pattern_score.fillna(0.5)
        
        # Smooth
        pattern_smooth = pattern_score.rolling(5).mean()
        
        return pd.DataFrame({
            'conv_uptrend': conv_uptrend,
            'conv_downtrend': conv_downtrend,
            'conv_volatility': conv_volatility,
            'pattern_score': pattern_score,
            'pattern_smooth': pattern_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong uptrend pattern detected
        entries = result['pattern_smooth'] > 0.6
        
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
        
        # Entry: Uptrend pattern
        entries = result['pattern_smooth'] > 0.6
        
        # Exit: Downtrend pattern
        exits = result['pattern_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pattern_reversal', index=data.index),
            'signal_strength': result['pattern_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['cnn_uptrend'] = result['conv_uptrend']
        features['cnn_downtrend'] = result['conv_downtrend']
        features['cnn_volatility'] = result['conv_volatility']
        features['cnn_pattern_score'] = result['pattern_score']
        features['cnn_pattern_smooth'] = result['pattern_smooth']
        features['cnn_strong_uptrend'] = (result['pattern_smooth'] > 0.7).astype(int)
        features['cnn_strong_downtrend'] = (result['pattern_smooth'] < 0.3).astype(int)
        
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

