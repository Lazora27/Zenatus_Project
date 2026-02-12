"""302 - Monte Carlo Probability Estimation"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MonteCarloProbability:
    """Monte Carlo Probability - Simulates future price paths"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'simulations': {'default': 100, 'values': [50,100,200,500], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MonteCarloProbability", "Probability", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        n_sims = params.get('simulations', 100)
        
        # Calculate historical volatility
        returns = np.log(data['close'] / data['close'].shift(1))
        volatility = returns.rolling(period).std()
        mean_return = returns.rolling(period).mean()
        
        # Monte Carlo simulation for next period
        prob_up = pd.Series(index=data.index, dtype=float)
        expected_return = pd.Series(index=data.index, dtype=float)
        
        for i in range(period, len(data)):
            if pd.isna(volatility.iloc[i]) or pd.isna(mean_return.iloc[i]):
                prob_up.iloc[i] = 0.5
                expected_return.iloc[i] = 0
                continue
            
            # Simulate n_sims paths
            current_price = data['close'].iloc[i]
            vol = volatility.iloc[i]
            mu = mean_return.iloc[i]
            
            # Simple Monte Carlo
            random_returns = np.random.normal(mu, vol, n_sims)
            simulated_prices = current_price * (1 + random_returns)
            
            # Probability of upward move
            prob_up.iloc[i] = (simulated_prices > current_price).sum() / n_sims
            expected_return.iloc[i] = (simulated_prices - current_price).mean() / current_price
        
        # Smooth probabilities
        prob_up_smooth = prob_up.rolling(5).mean()
        
        return pd.DataFrame({
            'prob_up': prob_up,
            'prob_up_smooth': prob_up_smooth,
            'expected_return': expected_return,
            'volatility': volatility
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High probability of upward move
        entries = result['prob_up_smooth'] > 0.6
        
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
            'signal_strength': result['prob_up_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High probability
        entries = result['prob_up_smooth'] > 0.6
        
        # Exit: Low probability
        exits = result['prob_up_smooth'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('mc_prob_change', index=data.index),
            'signal_strength': result['prob_up_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['prob_up'] = result['prob_up']
        features['prob_up_smooth'] = result['prob_up_smooth']
        features['expected_return'] = result['expected_return']
        features['volatility'] = result['volatility']
        features['high_prob'] = (result['prob_up_smooth'] > 0.6).astype(int)
        features['low_prob'] = (result['prob_up_smooth'] < 0.4).astype(int)
        features['prob_change'] = result['prob_up_smooth'].diff()
        
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

