"""321 - AutoML Optimizer"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AutoMLOptimizer:
    """AutoML Optimizer - Automatically selects best features and parameters"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_features': {'default': 5, 'values': [3,5,7,10], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AutoMLOptimizer", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_features = params.get('n_features', 5)
        
        # Feature pool
        returns = data['close'].pct_change()
        
        # Feature 1: Trend
        sma = data['close'].rolling(period).mean()
        trend_feature = ((data['close'] - sma) / sma).fillna(0)
        
        # Feature 2: Momentum
        momentum = data['close'] - data['close'].shift(5)
        momentum_feature = (momentum / data['close'].shift(5)).fillna(0)
        
        # Feature 3: Volatility
        volatility = returns.rolling(period).std()
        vol_feature = (volatility - volatility.rolling(period).mean()) / (volatility.rolling(period).std() + 1e-10)
        vol_feature = vol_feature.fillna(0)
        
        # Feature 4: Volume
        vol_ratio = data['volume'] / data['volume'].rolling(period).mean()
        volume_feature = (vol_ratio - 1).fillna(0)
        
        # Feature 5: RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        rsi_feature = (rsi - 50) / 50
        
        # Feature importance (correlation with future returns)
        future_returns = returns.shift(-1)
        
        features_df = pd.DataFrame({
            'trend': trend_feature,
            'momentum': momentum_feature,
            'volatility': vol_feature,
            'volume': volume_feature,
            'rsi': rsi_feature
        })
        
        # Calculate rolling correlations
        importances = []
        for col in features_df.columns:
            corr = features_df[col].rolling(period).corr(future_returns)
            importances.append(abs(corr))
        
        importance_df = pd.concat(importances, axis=1)
        importance_df.columns = features_df.columns
        
        # Select top features
        top_features = importance_df.apply(
            lambda x: x.nlargest(n_features).index.tolist() if len(x) > 0 else [],
            axis=1
        )
        
        # AutoML prediction (weighted by importance)
        automl_score = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            weights = importance_df.iloc[i].values
            weights = weights / (weights.sum() + 1e-10)
            
            feature_values = features_df.iloc[i].values
            automl_score.iloc[i] = np.dot(weights, feature_values)
        
        # Normalize to probability
        automl_prob = 1 / (1 + np.exp(-5 * automl_score))
        
        # Smooth
        automl_smooth = automl_prob.rolling(5).mean()
        
        return pd.DataFrame({
            'automl_score': automl_score,
            'automl_prob': automl_prob,
            'automl_smooth': automl_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High AutoML score
        entries = result['automl_smooth'] > 0.6
        
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
            'signal_strength': result['automl_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['automl_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['automl_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('automl_reversal', index=data.index),
            'signal_strength': result['automl_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['automl_score'] = result['automl_score']
        features['automl_prob'] = result['automl_prob']
        features['automl_smooth'] = result['automl_smooth']
        features['automl_high_prob'] = (result['automl_smooth'] > 0.6).astype(int)
        features['automl_low_prob'] = (result['automl_smooth'] < 0.4).astype(int)
        
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

