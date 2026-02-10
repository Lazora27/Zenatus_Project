"""116 - Sine Wave Indicator"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SineWave:
    """Sine Wave Indicator - Ehlers' sine wave oscillator"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SineWave", "Cycle", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Smooth price
        smooth = (4 * data['close'] + 3 * data['close'].shift(1) + 
                 2 * data['close'].shift(2) + data['close'].shift(3)) / 10
        
        # Detrender
        detrender = pd.Series(0.0, index=data.index)
        for i in range(6, len(data)):
            detrender.iloc[i] = (0.0962 * smooth.iloc[i] + 0.5769 * smooth.iloc[i-2] - 
                               0.5769 * smooth.iloc[i-4] - 0.0962 * smooth.iloc[i-6])
        
        # Compute InPhase and Quadrature
        inphase = pd.Series(0.0, index=data.index)
        quadrature = pd.Series(0.0, index=data.index)
        
        for i in range(3, len(data)):
            inphase.iloc[i] = detrender.iloc[i-3]
            if i >= 6:
                quadrature.iloc[i] = (0.0962 * detrender.iloc[i] + 0.5769 * detrender.iloc[i-2] - 
                                    0.5769 * detrender.iloc[i-4] - 0.0962 * detrender.iloc[i-6])
        
        # Smooth with 3-bar EMA
        sine = inphase.ewm(span=3).mean()
        lead_sine = quadrature.ewm(span=3).mean()
        
        return pd.DataFrame({'sine': sine, 'lead_sine': lead_sine}, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when sine crosses above lead_sine
        entries = (result['sine'] > result['lead_sine']) & (result['sine'].shift(1) <= result['lead_sine'].shift(1))
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 
                'signal_strength': abs(result['sine'] - result['lead_sine'])}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['sine'] > result['lead_sine']) & (result['sine'].shift(1) <= result['lead_sine'].shift(1))
        exits = (result['sine'] < result['lead_sine']) & (result['sine'].shift(1) >= result['lead_sine'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('sine_cross', index=data.index),
                'signal_strength': abs(result['sine'] - result['lead_sine'])}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({'sine': result['sine'], 'lead_sine': result['lead_sine'],
                           'sine_divergence': result['sine'] - result['lead_sine'],
                           'sine_positive': (result['sine'] > 0).astype(int),
                           'lead_positive': (result['lead_sine'] > 0).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
