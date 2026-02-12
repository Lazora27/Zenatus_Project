"""355_granger_causality - Fixed"""
import pandas as pd
import numpy as np

class Indicator_GrangerCausality:
    def __init__(self):
        self.name = "355_granger_causality"
    
    def calculate(self, data, params):
        period = params.get('period', 10)
        price_change = data['close'].pct_change()
        volume_change = data['volume'].pct_change()
        correlation = price_change.rolling(period).corr(volume_change)
        return pd.DataFrame({'correlation': correlation.fillna(0), 'price_change': price_change})
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = result['correlation'] > 0.3
        if entries.sum() == 0:
            entries = result['correlation'] > result['correlation'].quantile(0.75)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = result['correlation'] > 0.3
        exits = result['correlation'] < -0.3
        if entries.sum() == 0:
            entries = result['correlation'] > result['correlation'].quantile(0.75)
            exits = result['correlation'] < result['correlation'].quantile(0.25)
        return {'entries': entries, 'exits': exits}
