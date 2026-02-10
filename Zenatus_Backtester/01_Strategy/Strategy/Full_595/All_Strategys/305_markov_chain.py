"""305_markov_chain - Final Fix"""
import pandas as pd
import numpy as np

class Indicator_MarkovChain:
    def __init__(self):
        self.name = "305_markov_chain"
    
    def calculate(self, data, params):
        period = params.get('period', 10)
        
        # Simple state-based approach
        returns = data['close'].pct_change()
        
        # Define states: 0=down, 1=neutral, 2=up
        states = pd.cut(returns, bins=[-np.inf, -0.005, 0.005, np.inf], labels=[0, 1, 2])
        
        # Calculate transition probabilities
        prob_up = (states == 2).rolling(period).mean()
        prob_down = (states == 0).rolling(period).mean()
        prob_neutral = (states == 1).rolling(period).mean()
        
        # Trend strength
        trend_strength = prob_up - prob_down
        
        return pd.DataFrame({
            'prob_up': prob_up.fillna(0.33),
            'prob_down': prob_down.fillna(0.33),
            'prob_neutral': prob_neutral.fillna(0.33),
            'trend_strength': trend_strength.fillna(0)
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry when probability of up movement is high (LOWERED THRESHOLD)
        entries = result['prob_up'] > 0.4
        
        # Fallback if no entries
        if entries.sum() == 0:
            entries = result['trend_strength'] > result['trend_strength'].quantile(0.6)
        
        # Final fallback
        if entries.sum() == 0:
            entries = result['prob_up'] > result['prob_up'].quantile(0.7)
        
        return {
            'entries': entries,
            'exits': pd.Series([False] * len(data), index=data.index)
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry when probability of up movement is high (LOWERED THRESHOLD)
        entries = result['prob_up'] > 0.4
        
        # Exit when probability of down movement is high
        exits = result['prob_down'] > 0.4
        
        # Fallback if no entries
        if entries.sum() == 0:
            entries = result['trend_strength'] > result['trend_strength'].quantile(0.6)
            exits = result['trend_strength'] < result['trend_strength'].quantile(0.4)
        
        # Final fallback
        if entries.sum() == 0:
            entries = result['prob_up'] > result['prob_up'].quantile(0.7)
            exits = result['prob_down'] > result['prob_down'].quantile(0.7)
        
        return {
            'entries': entries,
            'exits': exits
        }
