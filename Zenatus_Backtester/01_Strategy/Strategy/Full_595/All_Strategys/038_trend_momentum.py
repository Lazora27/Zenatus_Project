"""038_trend_momentum - Fixed"""
import pandas as pd
import numpy as np

class Indicator_Momentum:
    def __init__(self):
        self.name = "038_trend_momentum"
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        momentum = data['close'].diff(period)
        return pd.DataFrame({'momentum': momentum, 'momentum_ma': momentum.rolling(period).mean()})
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = result['momentum'] > 0.0005  # Sehr niedriger Threshold
        if entries.sum() == 0:
            entries = result['momentum'] > result['momentum'].quantile(0.8)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = result['momentum'] > 0.0005
        exits = result['momentum'] < -0.0005
        if entries.sum() == 0:
            entries = result['momentum'] > result['momentum'].quantile(0.8)
            exits = result['momentum'] < result['momentum'].quantile(0.2)
        return {'entries': entries, 'exits': exits}
