"""335 - Automated Feature Engineering"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FeatureEngineeringAuto:
    """Automated Feature Engineering - Automatically generates and tests features"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FeatureEngineeringAuto", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Automatically generate features
        returns = data['close'].pct_change()
        
        auto_features = {}
        
        # Time-based features
        auto_features['returns_1'] = returns
        auto_features['returns_5'] = returns.rolling(5).sum()
        auto_features['returns_10'] = returns.rolling(10).sum()
        
        # Statistical features
        auto_features['mean'] = data['close'].rolling(period).mean()
        auto_features['std'] = data['close'].rolling(period).std()
        auto_features['skew'] = returns.rolling(period).skew()
        auto_features['kurt'] = returns.rolling(period).kurt()
        
        # Ratio features
        auto_features['high_low_ratio'] = data['high'] / (data['low'] + 1e-10)
        auto_features['close_open_ratio'] = data['close'] / (data['open'] + 1e-10)
        
        # Lag features
        auto_features['lag_1'] = data['close'].shift(1)
        auto_features['lag_5'] = data['close'].shift(5)
        
        # Rolling features
        auto_features['rolling_max'] = data['close'].rolling(period).max()
        auto_features['rolling_min'] = data['close'].rolling(period).min()
        
        # Difference features
        auto_features['diff_1'] = data['close'].diff(1)
        auto_features['diff_5'] = data['close'].diff(5)
        
        auto_df = pd.DataFrame(auto_features)
        
        # Normalize all features
        auto_normalized = pd.DataFrame(index=data.index)
        
        for col in auto_df.columns:
            col_mean = auto_df[col].rolling(period).mean()
            col_std = auto_df[col].rolling(period).std()
            auto_normalized[col] = (auto_df[col] - col_mean) / (col_std + 1e-10)
        
        # Aggregate score
        auto_score = auto_normalized.fillna(0).mean(axis=1)
        
        # Normalize to probability
        auto_prob = 1 / (1 + np.exp(-2 * auto_score))
        
        # Smooth
        auto_smooth = auto_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'auto_score': auto_score,
            'auto_prob': auto_prob,
            'auto_smooth': auto_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High auto score
        entries = result['auto_smooth'] > 0.6
        
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
            'signal_strength': result['auto_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['auto_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['auto_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('auto_reversal', index=data.index),
            'signal_strength': result['auto_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['auto_score'] = result['auto_score']
        features['auto_prob'] = result['auto_prob']
        features['auto_smooth'] = result['auto_smooth']
        features['auto_high_score'] = (result['auto_smooth'] > 0.6).astype(int)
        features['auto_low_score'] = (result['auto_smooth'] < 0.4).astype(int)
        
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

