"""331 - Feature Importance Ranker"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FeatureImportanceRanker:
    """Feature Importance Ranker - Ranks and selects most predictive features"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'top_n': {'default': 3, 'values': [2,3,4,5], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FeatureImportanceRanker", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        top_n = params.get('top_n', 3)
        
        # Create feature set
        returns = data['close'].pct_change()
        
        features = {}
        
        # Feature 1: Price momentum
        features['momentum_5'] = (data['close'] - data['close'].shift(5)) / data['close'].shift(5)
        features['momentum_10'] = (data['close'] - data['close'].shift(10)) / data['close'].shift(10)
        
        # Feature 2: Volatility
        features['volatility'] = returns.rolling(period).std()
        
        # Feature 3: Volume
        features['volume_ratio'] = data['volume'] / data['volume'].rolling(period).mean()
        
        # Feature 4: RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # Feature 5: MACD
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        
        # Feature 6: Bollinger position
        sma = data['close'].rolling(period).mean()
        bb_std = data['close'].rolling(period).std()
        features['bb_position'] = (data['close'] - sma) / (bb_std + 1e-10)
        
        features_df = pd.DataFrame(features)
        
        # Calculate importance (correlation with future returns)
        future_returns = returns.shift(-1)
        
        importance_scores = pd.DataFrame(index=data.index)
        
        for col in features_df.columns:
            corr = features_df[col].rolling(period).corr(future_returns)
            importance_scores[col] = abs(corr)
        
        # Rank features
        feature_ranks = importance_scores.rank(axis=1, ascending=False)
        
        # Select top features
        top_feature_score = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Get top N features
            top_features = importance_scores.iloc[i].nlargest(top_n)
            
            if len(top_features) > 0:
                # Weighted score from top features
                weights = top_features.values / (top_features.sum() + 1e-10)
                feature_values = features_df.iloc[i][top_features.index].values
                
                # Normalize feature values
                feature_values = (feature_values - feature_values.mean()) / (feature_values.std() + 1e-10)
                
                top_feature_score.iloc[i] = np.dot(weights, feature_values)
        
        # Normalize to probability
        feature_prob = 1 / (1 + np.exp(-2 * top_feature_score))
        
        # Smooth
        feature_smooth = feature_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'top_feature_score': top_feature_score,
            'feature_prob': feature_prob,
            'feature_smooth': feature_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High feature score
        entries = result['feature_smooth'] > 0.6
        
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
            'signal_strength': result['feature_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['feature_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['feature_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('feature_reversal', index=data.index),
            'signal_strength': result['feature_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['fi_score'] = result['top_feature_score']
        features['fi_prob'] = result['feature_prob']
        features['fi_smooth'] = result['feature_smooth']
        features['fi_high_score'] = (result['feature_smooth'] > 0.6).astype(int)
        features['fi_low_score'] = (result['feature_smooth'] < 0.4).astype(int)
        
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

