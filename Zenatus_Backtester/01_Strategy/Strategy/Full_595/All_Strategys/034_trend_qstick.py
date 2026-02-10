"""034_trend_qstick - Fixed"""
import pandas as pd
import numpy as np

class Indicator_Qstick:
    def __init__(self):
        self.name = "034_trend_qstick"
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        qstick = (data['close'] - data['open']).rolling(period).mean()
        return qstick
    
    def generate_signals_fixed(self, data, params):
        qstick = self.calculate(data, params)
        entries = qstick > 0.0001  # Sehr niedriger Threshold
        if entries.sum() == 0:
            entries = qstick > qstick.quantile(0.7)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        qstick = self.calculate(data, params)
        entries = qstick > 0.0001
        exits = qstick < -0.0001
        if entries.sum() == 0:
            entries = qstick > qstick.quantile(0.7)
            exits = qstick < qstick.quantile(0.3)
        return {'entries': entries, 'exits': exits}
