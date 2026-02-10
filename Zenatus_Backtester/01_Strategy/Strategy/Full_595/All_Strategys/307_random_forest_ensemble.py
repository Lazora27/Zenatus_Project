"""307 - Random Forest Ensemble Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RandomForestEnsemble:
    """Random Forest Ensemble - Multiple decision tree based signals"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'n_trees': {'default': 10, 'values': [5,10,15,20], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RandomForestEnsemble", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_trees = params.get('n_trees', 10)
        
        # Create multiple simple decision rules (trees)
        votes = []
        
        # Tree 1: Price vs SMA
        sma = data['close'].rolling(period).mean()
        votes.append((data['close'] > sma).astype(int))
        
        # Tree 2: RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        votes.append((rsi < 70).astype(int))
        
        # Tree 3: Volume
        vol_ma = data['volume'].rolling(period).mean()
        votes.append((data['volume'] > vol_ma).astype(int))
        
        # Tree 4: Momentum
        momentum = data['close'] - data['close'].shift(5)
        votes.append((momentum > 0).astype(int))
        
        # Tree 5: Volatility
        returns = data['close'].pct_change()
        volatility = returns.rolling(period).std()
        vol_ma = volatility.rolling(period).mean()
        votes.append((volatility < vol_ma * 1.5).astype(int))
        
        # Tree 6: MACD
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        votes.append((macd > 0).astype(int))
        
        # Tree 7: Bollinger Bands
        bb_std = data['close'].rolling(period).std()
        bb_upper = sma + 2 * bb_std
        bb_lower = sma - 2 * bb_std
        votes.append((data['close'] > bb_lower).astype(int))
        
        # Tree 8: ADX
        high_low = data['high'] - data['low']
        tr = high_low.rolling(period).mean()
        plus_dm = (data['high'] - data['high'].shift(1)).clip(lower=0)
        adx_signal = plus_dm.rolling(period).mean() / tr
        votes.append((adx_signal > 0.3).astype(int))
        
        # Tree 9: Stochastic
        low_min = data['low'].rolling(period).min()
        high_max = data['high'].rolling(period).max()
        stoch = (data['close'] - low_min) / (high_max - low_min + 1e-10) * 100
        votes.append((stoch < 80).astype(int))
        
        # Tree 10: Price pattern
        higher_high = data['high'] > data['high'].shift(1)
        higher_low = data['low'] > data['low'].shift(1)
        votes.append((higher_high & higher_low).astype(int))
        
        # Ensemble voting
        votes_df = pd.concat(votes[:n_trees], axis=1)
        ensemble_score = votes_df.mean(axis=1)
        
        # Confidence
        vote_std = votes_df.std(axis=1)
        confidence = 1 - vote_std
        
        return pd.DataFrame({
            'ensemble_score': ensemble_score,
            'confidence': confidence,
            'n_votes_bullish': votes_df.sum(axis=1)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Majority vote bullish
        entries = result['ensemble_score'] > 0.6
        
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
            'signal_strength': result['confidence']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Majority bullish
        entries = result['ensemble_score'] > 0.6
        
        # Exit: Majority bearish
        exits = result['ensemble_score'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('ensemble_reversal', index=data.index),
            'signal_strength': result['confidence']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['rf_ensemble_score'] = result['ensemble_score']
        features['rf_confidence'] = result['confidence']
        features['rf_votes_bullish'] = result['n_votes_bullish']
        features['rf_strong_bullish'] = (result['ensemble_score'] > 0.7).astype(int)
        features['rf_strong_bearish'] = (result['ensemble_score'] < 0.3).astype(int)
        features['rf_high_confidence'] = (result['confidence'] > 0.7).astype(int)
        
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

