"""416 - Market Making Spread"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MarketMakingSpread:
    """Market Making Spread - Optimal bid-ask spread for market makers"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'risk_aversion': {'default': 0.5, 'values': [0.3,0.5,0.7], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MarketMakingSpread", "HFT_Microstructure", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        gamma = params.get('risk_aversion', 0.5)
        
        # Volatility
        returns = data['close'].pct_change().fillna(0)
        volatility = returns.rolling(period).std()
        
        # Trade intensity (arrival rate)
        volume_rate = data['volume'] / data['volume'].rolling(period).mean()
        
        # Optimal spread = γ * σ² + (2/γ) * log(1 + γ/k)
        # Simplified: spread ∝ volatility * risk_aversion
        optimal_spread = gamma * volatility * volatility
        
        # Adjust for trade intensity
        optimal_spread_adjusted = optimal_spread / (volume_rate + 1e-10)
        
        # Normalize
        spread_normalized = optimal_spread_adjusted / (optimal_spread_adjusted.rolling(50).max() + 1e-10)
        
        # Profitability score (inverse of spread)
        profitability = 1 / (spread_normalized + 1e-10)
        profitability_normalized = profitability / profitability.rolling(50).max()
        
        # Smooth
        profitability_smooth = profitability_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'volatility': volatility,
            'volume_rate': volume_rate,
            'optimal_spread': optimal_spread,
            'optimal_spread_adjusted': optimal_spread_adjusted,
            'spread_normalized': spread_normalized,
            'profitability': profitability_normalized,
            'profitability_smooth': profitability_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High profitability (low spread)
        entries = result['profitability_smooth'] > 0.6
        
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
            'signal_strength': result['profitability_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Profitable
        entries = result['profitability'] > 0.6
        
        # Exit: Unprofitable
        exits = result['profitability'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('wide_spread', index=data.index),
            'signal_strength': result['profitability_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['mm_volatility'] = result['volatility']
        features['mm_volume_rate'] = result['volume_rate']
        features['mm_optimal_spread'] = result['optimal_spread']
        features['mm_optimal_spread_adjusted'] = result['optimal_spread_adjusted']
        features['mm_spread_normalized'] = result['spread_normalized']
        features['mm_profitability'] = result['profitability']
        features['mm_profitability_smooth'] = result['profitability_smooth']
        features['mm_profitable'] = (result['profitability'] > 0.6).astype(int)
        
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

