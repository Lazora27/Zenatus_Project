"""308 - Neural Network Prediction (Simplified)"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_NeuralNetworkPrediction:
    """Neural Network Prediction - Simplified NN-based prediction"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'hidden_size': {'default': 10, 'values': [5,10,15,20], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "NeuralNetworkPrediction", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Simplified neural network using weighted features
        # Input layer: normalized features
        returns = data['close'].pct_change()
        
        # Feature 1: Normalized price
        price_norm = (data['close'] - data['close'].rolling(period).min()) / (
            data['close'].rolling(period).max() - data['close'].rolling(period).min() + 1e-10
        )
        
        # Feature 2: Momentum
        momentum = (data['close'] - data['close'].shift(5)) / data['close'].shift(5)
        momentum_norm = (momentum - momentum.rolling(period).mean()) / (momentum.rolling(period).std() + 1e-10)
        
        # Feature 3: Volume
        vol_norm = (data['volume'] - data['volume'].rolling(period).min()) / (
            data['volume'].rolling(period).max() - data['volume'].rolling(period).min() + 1e-10
        )
        
        # Feature 4: Volatility
        volatility = returns.rolling(period).std()
        vol_rank = volatility.rolling(100).apply(
            lambda x: pd.Series(x).rank().iloc[-1] / len(x) if len(x) > 0 else 0.5
        )
        
        # Hidden layer (simplified): weighted sum with activation
        hidden = (
            0.4 * price_norm.fillna(0.5) +
            0.3 * momentum_norm.fillna(0).clip(-3, 3) / 3 +
            0.2 * vol_norm.fillna(0.5) +
            0.1 * vol_rank.fillna(0.5)
        )
        
        # Activation function (sigmoid-like)
        hidden_activated = 1 / (1 + np.exp(-5 * (hidden - 0.5)))
        
        # Output layer: prediction
        prediction = hidden_activated
        
        # Smooth prediction
        prediction_smooth = prediction.rolling(5).mean()
        
        return pd.DataFrame({
            'prediction': prediction,
            'prediction_smooth': prediction_smooth,
            'price_norm': price_norm,
            'momentum_norm': momentum_norm,
            'vol_norm': vol_norm
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High prediction
        entries = result['prediction_smooth'] > 0.6
        
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
            'signal_strength': result['prediction_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High prediction
        entries = result['prediction_smooth'] > 0.6
        
        # Exit: Low prediction
        exits = result['prediction_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('nn_reversal', index=data.index),
            'signal_strength': result['prediction_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['nn_prediction'] = result['prediction']
        features['nn_prediction_smooth'] = result['prediction_smooth']
        features['nn_price_norm'] = result['price_norm']
        features['nn_momentum_norm'] = result['momentum_norm']
        features['nn_vol_norm'] = result['vol_norm']
        features['nn_high_pred'] = (result['prediction_smooth'] > 0.6).astype(int)
        features['nn_low_pred'] = (result['prediction_smooth'] < 0.4).astype(int)
        
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

