"""303 - Statistical Arbitrage Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_StatisticalArbitrage:
    """Statistical Arbitrage - Mean reversion based on statistical analysis"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'zscore_threshold': {'default': 2.0, 'values': [1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "StatisticalArbitrage", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('zscore_threshold', 2.0)
        
        # Calculate z-score
        price_ma = data['close'].rolling(period).mean()
        price_std = data['close'].rolling(period).std()
        zscore = (data['close'] - price_ma) / (price_std + 1e-10)
        
        # Mean reversion signals
        oversold = zscore < -threshold
        overbought = zscore > threshold
        
        # Half-life of mean reversion
        def calc_half_life(prices):
            if len(prices) < 2:
                return period / 2
            lag = prices.shift(1).dropna()
            ret = prices[1:] - lag
            lag = lag[ret.index]
            if len(lag) == 0 or lag.std() == 0:
                return period / 2
            beta = np.polyfit(lag, ret, 1)[0]
            if beta >= 0:
                return period / 2
            return -np.log(2) / beta
        
        half_life = data['close'].rolling(period).apply(calc_half_life, raw=False)
        
        # Mean reversion strength
        reversion_strength = abs(zscore) / threshold
        
        return pd.DataFrame({
            'zscore': zscore,
            'price_ma': price_ma,
            'price_std': price_std,
            'oversold': oversold.astype(int),
            'overbought': overbought.astype(int),
            'half_life': half_life,
            'reversion_strength': reversion_strength
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Oversold (expect mean reversion up)
        entries = result['oversold'] == 1
        
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
            'signal_strength': result['reversion_strength'].clip(0, 2) / 2
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Oversold
        entries = result['oversold'] == 1
        
        # Exit: Return to mean or overbought
        exits = (abs(result['zscore']) < 0.5) | (result['overbought'] == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('mean_reversion', index=data.index),
            'signal_strength': result['reversion_strength'].clip(0, 2) / 2
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['zscore'] = result['zscore']
        features['oversold'] = result['oversold']
        features['overbought'] = result['overbought']
        features['half_life'] = result['half_life']
        features['reversion_strength'] = result['reversion_strength']
        features['distance_from_mean'] = abs(result['zscore'])
        features['extreme_zscore'] = (abs(result['zscore']) > 2).astype(int)
        
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

