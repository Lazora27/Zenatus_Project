"""413_hasbrouck_information_share - Fixed"""
import pandas as pd
import numpy as np

class Indicator_HasbrouckInformationShare:
    def __init__(self):
        self.name = "413_hasbrouck_information_share"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        price_impact = data['close'].diff() / (data['volume'] + 1e-10)
        info_share = price_impact.rolling(period).std()
        return pd.DataFrame({'info_share': info_share.fillna(0), 'price_impact': price_impact})
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        entries = result['info_share'] > result['info_share'].quantile(0.8)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = result['info_share'] > result['info_share'].quantile(0.8)
        exits = result['info_share'] < result['info_share'].quantile(0.2)
        return {'entries': entries, 'exits': exits}
