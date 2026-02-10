"""086 - FRAMA (Fractal Adaptive Moving Average) - Extended"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FRAMAExtended:
    """FRAMA Extended - Fractal Adaptive Moving Average with enhanced features"""
    PARAMETERS = {
        'period': {'default': 16, 'values': [8,11,13,14,16,19,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FRAMAExtended", "Trend", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 16)
        
        # Fractal Dimension calculation
        n = int(period / 2)
        
        # High/Low for each half
        high1 = data['high'].rolling(n).max()
        low1 = data['low'].rolling(n).min()
        high2 = data['high'].shift(n).rolling(n).max()
        low2 = data['low'].shift(n).rolling(n).min()
        
        # Fractal dimensions
        n1 = (high1 - low1) / n
        n2 = (high2 - low2) / n
        n3 = (data['high'].rolling(period).max() - data['low'].rolling(period).min()) / period
        
        # Dimension
        dimen = (np.log(n1 + n2) - np.log(n3)) / np.log(2)
        dimen = dimen.clip(1, 2)
        
        # Alpha
        alpha = np.exp(-4.6 * (dimen - 1))
        alpha = alpha.clip(0.01, 1)
        
        # FRAMA
        frama = pd.Series(index=data.index, dtype=float)
        frama.iloc[0] = data['close'].iloc[0]
        
        for i in range(1, len(data)):
            if pd.notna(alpha.iloc[i]):
                frama.iloc[i] = alpha.iloc[i] * data['close'].iloc[i] + (1 - alpha.iloc[i]) * frama.iloc[i-1]
            else:
                frama.iloc[i] = frama.iloc[i-1]
        
        return frama.fillna(data['close'])
    
    def generate_signals_fixed(self, data, params):
        frama = self.calculate(data, params)
        # Entry when price crosses above FRAMA
        entries = (data['close'] > frama) & (data['close'].shift(1) <= frama.shift(1))
        
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
                'signal_strength': abs(data['close'] - frama) / (frama + 1e-10)}
    
    def generate_signals_dynamic(self, data, params):
        frama = self.calculate(data, params)
        entries = (data['close'] > frama) & (data['close'].shift(1) <= frama.shift(1))
        exits = (data['close'] < frama) & (data['close'].shift(1) >= frama.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('frama_cross', index=data.index),
                'signal_strength': abs(data['close'] - frama) / (frama + 1e-10)}
    
    def get_ml_features(self, data, params):
        frama = self.calculate(data, params)
        return pd.DataFrame({'frama_value': frama, 'frama_slope': frama.diff(),
                           'price_above_frama': (data['close'] > frama).astype(int),
                           'distance_from_frama': data['close'] - frama}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
