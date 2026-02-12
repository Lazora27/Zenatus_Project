"""332 - Feature Selection Filter"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FeatureSelectionFilter:
    """Feature Selection Filter - Filters out redundant and irrelevant features"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'correlation_threshold': {'default': 0.3, 'values': [0.2,0.3,0.4,0.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FeatureSelectionFilter", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        corr_threshold = params.get('correlation_threshold', 0.3)
        
        # Create diverse features
        returns = data['close'].pct_change()
        
        features = {}
        
        # Price-based features
        features['price_change'] = returns
        features['price_acceleration'] = returns.diff()
        
        # Momentum features
        features['momentum_short'] = data['close'] - data['close'].shift(5)
        features['momentum_long'] = data['close'] - data['close'].shift(20)
        
        # Volatility features
        features['volatility'] = returns.rolling(period).std()
        features['volatility_change'] = features['volatility'].diff()
        
        # Volume features
        features['volume_change'] = data['volume'].pct_change()
        features['volume_ma_ratio'] = data['volume'] / data['volume'].rolling(period).mean()
        
        features_df = pd.DataFrame(features)
        
        # Filter features based on correlation with target
        future_returns = returns.shift(-1)
        
        selected_features = pd.DataFrame(index=data.index)
        
        for i in range(period, len(data)):
            # Calculate correlations
            correlations = {}
            
            for col in features_df.columns:
                corr = features_df[col].iloc[i-period:i].corr(future_returns.iloc[i-period:i])
                if not np.isnan(corr):
                    correlations[col] = abs(corr)
            
            # Select features above threshold
            selected = {k: v for k, v in correlations.items() if v > corr_threshold}
            
            # Calculate score from selected features
            if len(selected) > 0:
                weights = np.array(list(selected.values()))
                weights = weights / weights.sum()
                
                feature_vals = features_df.iloc[i][list(selected.keys())].values
                feature_vals = (feature_vals - np.mean(feature_vals)) / (np.std(feature_vals) + 1e-10)
                
                selected_features.loc[data.index[i], 'score'] = np.dot(weights, feature_vals)
                selected_features.loc[data.index[i], 'n_selected'] = len(selected)
            else:
                selected_features.loc[data.index[i], 'score'] = 0
                selected_features.loc[data.index[i], 'n_selected'] = 0
        
        # Normalize score
        filtered_prob = 1 / (1 + np.exp(-3 * selected_features['score'].fillna(0)))
        
        # Smooth
        filtered_smooth = filtered_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'filtered_score': selected_features['score'].fillna(0),
            'n_selected_features': selected_features['n_selected'].fillna(0),
            'filtered_prob': filtered_prob,
            'filtered_smooth': filtered_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High filtered score
        entries = result['filtered_smooth'] > 0.6
        
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
            'signal_strength': result['filtered_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['filtered_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['filtered_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('feature_reversal', index=data.index),
            'signal_strength': result['filtered_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['fs_score'] = result['filtered_score']
        features['fs_n_selected'] = result['n_selected_features']
        features['fs_prob'] = result['filtered_prob']
        features['fs_smooth'] = result['filtered_smooth']
        features['fs_high_score'] = (result['filtered_smooth'] > 0.6).astype(int)
        features['fs_many_features'] = (result['n_selected_features'] > 3).astype(int)
        
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

