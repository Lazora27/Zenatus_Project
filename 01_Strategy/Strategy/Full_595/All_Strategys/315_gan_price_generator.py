"""315 - GAN-Inspired Price Pattern Generator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_GANPriceGenerator:
    """GAN Price Generator - Discriminates real vs synthetic patterns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "GANPriceGenerator", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Real pattern features
        returns = data['close'].pct_change()
        
        # Generator: Create synthetic pattern
        noise = pd.Series(np.random.randn(len(data)), index=data.index)
        synthetic_returns = returns.rolling(period).mean() + noise * returns.rolling(period).std()
        
        # Discriminator: Distinguish real from synthetic
        # Feature 1: Autocorrelation
        real_autocorr = returns.rolling(period).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0,
            raw=True
        )
        
        # Feature 2: Distribution shape
        real_skew = returns.rolling(period).skew()
        real_kurt = returns.rolling(period).kurt()
        
        # Feature 3: Volatility clustering
        vol_cluster = (returns**2).rolling(5).mean()
        
        # Discriminator score (how "real" the pattern is)
        # High score = pattern is typical/expected
        # Low score = pattern is unusual/opportunity
        discriminator_score = (
            0.4 * (abs(real_autocorr) < 0.5).astype(float) +
            0.3 * (abs(real_skew) < 1.0).astype(float) +
            0.3 * (abs(real_kurt) < 3.0).astype(float)
        )
        
        # Smooth
        discriminator_smooth = discriminator_score.rolling(5).mean()
        
        # Unusual pattern (low discriminator score = opportunity)
        unusual_pattern = discriminator_smooth < 0.4
        
        return pd.DataFrame({
            'discriminator_score': discriminator_score,
            'discriminator_smooth': discriminator_smooth,
            'real_autocorr': real_autocorr,
            'real_skew': real_skew,
            'real_kurt': real_kurt,
            'unusual_pattern': unusual_pattern.astype(int)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Unusual pattern with upward momentum
        price_up = data['close'] > data['close'].shift(1)
        entries = (result['unusual_pattern'] == 1) & price_up
        
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
            'signal_strength': (1 - result['discriminator_smooth'])
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Unusual pattern
        entries = result['unusual_pattern'] == 1
        
        # Exit: Pattern becomes typical again
        exits = (result['unusual_pattern'] == 0) & (result['unusual_pattern'].shift(1) == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pattern_normalized', index=data.index),
            'signal_strength': (1 - result['discriminator_smooth'])
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['gan_discriminator'] = result['discriminator_score']
        features['gan_discriminator_smooth'] = result['discriminator_smooth']
        features['gan_autocorr'] = result['real_autocorr']
        features['gan_skew'] = result['real_skew']
        features['gan_kurt'] = result['real_kurt']
        features['gan_unusual_pattern'] = result['unusual_pattern']
        features['gan_typical_pattern'] = (result['discriminator_smooth'] > 0.6).astype(int)
        
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

