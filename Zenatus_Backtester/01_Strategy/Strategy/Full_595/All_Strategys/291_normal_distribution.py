"""291_normal_distribution - Fixed"""
import pandas as pd
import numpy as np

class Indicator_NormalDistribution:
    def __init__(self):
        self.name = "291_normal_distribution"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        returns = data['close'].pct_change()
        rolling_mean = returns.rolling(period).mean()
        rolling_std = returns.rolling(period).std()
        z_score = (returns - rolling_mean) / (rolling_std + 1e-10)
        return pd.DataFrame({'z_score': z_score.fillna(0), 'mean': rolling_mean, 'std': rolling_std})
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = result['z_score'] > 1.5
        if entries.sum() == 0:
            entries = result['z_score'] > result['z_score'].quantile(0.85)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = result['z_score'] > 1.5
        exits = result['z_score'] < -1.5
        if entries.sum() == 0:
            entries = result['z_score'] > result['z_score'].quantile(0.85)
            exits = result['z_score'] < result['z_score'].quantile(0.15)
        return {'entries': entries, 'exits': exits}
