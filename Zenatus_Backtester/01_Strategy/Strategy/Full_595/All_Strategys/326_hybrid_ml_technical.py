"""326 - Hybrid ML-Technical Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HybridMLTechnical:
    """Hybrid ML-Technical - Combines ML predictions with technical analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'ml_weight': {'default': 0.5, 'values': [0.3,0.4,0.5,0.6,0.7], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HybridMLTechnical", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        ml_weight = params.get('ml_weight', 0.5)
        tech_weight = 1 - ml_weight
        
        # ML Component: Pattern recognition
        returns = data['close'].pct_change()
        
        # Simple ML predictor
        momentum = data['close'] - data['close'].shift(5)
        volatility = returns.rolling(period).std()
        vol_ratio = data['volume'] / data['volume'].rolling(period).mean()
        
        ml_features = pd.DataFrame({
            'momentum': (momentum / data['close'].shift(5)).fillna(0),
            'volatility': (volatility - volatility.rolling(period).mean()).fillna(0) / (volatility.rolling(period).std() + 1e-10),
            'volume': (vol_ratio - 1).fillna(0)
        })
        
        ml_score = ml_features.mean(axis=1)
        ml_prob = 1 / (1 + np.exp(-5 * ml_score))
        
        # Technical Component: Classic indicators
        # RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        
        # Bollinger Bands
        sma = data['close'].rolling(period).mean()
        bb_std = data['close'].rolling(period).std()
        bb_position = (data['close'] - sma) / (2 * bb_std + 1e-10)
        
        # Technical score
        tech_score = (
            0.4 * ((rsi < 70).astype(float)) +
            0.3 * ((macd > 0).astype(float)) +
            0.3 * ((bb_position > -1).astype(float))
        )
        
        # Hybrid combination
        hybrid_score = ml_weight * ml_prob + tech_weight * tech_score
        
        # Smooth
        hybrid_smooth = hybrid_score.rolling(5).mean()
        
        return pd.DataFrame({
            'ml_prob': ml_prob,
            'tech_score': tech_score,
            'hybrid_score': hybrid_score,
            'hybrid_smooth': hybrid_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High hybrid score
        entries = result['hybrid_smooth'] > 0.6
        
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
            'signal_strength': result['hybrid_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['hybrid_smooth'] > 0.6
        
        # Exit: Low score
        exits = result['hybrid_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('hybrid_reversal', index=data.index),
            'signal_strength': result['hybrid_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['hybrid_ml_prob'] = result['ml_prob']
        features['hybrid_tech_score'] = result['tech_score']
        features['hybrid_score'] = result['hybrid_score']
        features['hybrid_smooth'] = result['hybrid_smooth']
        features['hybrid_high_score'] = (result['hybrid_smooth'] > 0.6).astype(int)
        features['hybrid_low_score'] = (result['hybrid_smooth'] < 0.4).astype(int)
        
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

