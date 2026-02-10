"""049_volume_cmf - Fixed"""
import pandas as pd
import numpy as np

class Indicator_CMF:
    def __init__(self):
        self.name = "049_volume_cmf"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        mfm = ((data['close'] - data['low']) - (data['high'] - data['close'])) / (data['high'] - data['low'] + 1e-10)
        mfv = mfm * data['volume']
        cmf = mfv.rolling(period).sum() / (data['volume'].rolling(period).sum() + 1e-10)
        return cmf.fillna(0)
    
    def generate_signals_fixed(self, data, params):
        cmf = self.calculate(data, params)
        entries = cmf > 0.05  # Niedriger Threshold
        if entries.sum() == 0:
            entries = cmf > cmf.quantile(0.75)
        return {'entries': entries, 'exits': pd.Series([False] * len(data), index=data.index)}
    
    def generate_signals_dynamic(self, data, params):
        cmf = self.calculate(data, params)
        entries = cmf > 0.05
        exits = cmf < -0.05
        if entries.sum() == 0:
            entries = cmf > cmf.quantile(0.75)
            exits = cmf < cmf.quantile(0.25)
        return {'entries': entries, 'exits': exits}
