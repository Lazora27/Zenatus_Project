"""152_volume_divergenceconfluence - Simplified"""
import pandas as pd
import numpy as np

class Indicator_DivergenceConfluence:
    def __init__(self):
        self.name = "152_volume_divergenceconfluence"
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        price_roc = data['close'].pct_change(period)
        volume_roc = data['volume'].pct_change(period)
        divergence = (price_roc * volume_roc < 0).astype(int)
        strength = abs(price_roc - volume_roc)
        return pd.DataFrame({'divergence': divergence, 'strength': strength.fillna(0)})
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = (result['divergence'] == 1) & (result['strength'] > result['strength'].quantile(0.7))
        if entries.sum() == 0:
            entries = result['strength'] > result['strength'].quantile(0.85)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['divergence'] == 1) & (result['strength'] > result['strength'].quantile(0.7))
        exits = result['divergence'] == 0
        if entries.sum() == 0:
            entries = result['strength'] > result['strength'].quantile(0.85)
            exits = result['strength'] < result['strength'].quantile(0.15)
        return {'entries': entries, 'exits': exits}
