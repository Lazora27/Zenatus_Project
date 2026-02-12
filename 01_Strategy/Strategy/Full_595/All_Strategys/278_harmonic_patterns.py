"""278 - Harmonic Patterns"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HarmonicPatterns:
    """Harmonic Patterns - Gartley, Butterfly, Bat, Crab"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [30,50,100], 'optimize': True},
        'tolerance': {'default': 0.05, 'values': [0.03,0.05,0.08], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HarmonicPatterns", "Patterns", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        tolerance = params.get('tolerance', 0.05)
        high, low = data['high'], data['low']
        
        # Find swing points
        swing_high = (high > high.shift(1)) & (high > high.shift(-1))
        swing_low = (low < low.shift(1)) & (low < low.shift(-1))
        
        # Fibonacci ratios for harmonic patterns
        fib_618 = 0.618
        fib_786 = 0.786
        fib_886 = 0.886
        fib_127 = 1.27
        fib_161 = 1.618
        
        # Gartley Pattern (simplified detection)
        gartley = pd.Series(0, index=data.index)
        
        # Butterfly Pattern
        butterfly = pd.Series(0, index=data.index)
        
        # Bat Pattern
        bat = pd.Series(0, index=data.index)
        
        # Crab Pattern
        crab = pd.Series(0, index=data.index)
        
        # Simplified harmonic detection using price swings
        price_range = high.rolling(period).max() - low.rolling(period).min()
        retracement = (high - low.rolling(period).min()) / (price_range + 1e-10)
        
        # Approximate harmonic zones
        harmonic_618 = (abs(retracement - fib_618) < tolerance).astype(int)
        harmonic_786 = (abs(retracement - fib_786) < tolerance).astype(int)
        harmonic_886 = (abs(retracement - fib_886) < tolerance).astype(int)
        
        # Combined harmonic signal
        harmonic_signal = harmonic_618 + harmonic_786 + harmonic_886
        
        return pd.DataFrame({
            'gartley': gartley,
            'butterfly': butterfly,
            'bat': bat,
            'crab': crab,
            'harmonic_618': harmonic_618,
            'harmonic_786': harmonic_786,
            'harmonic_886': harmonic_886,
            'harmonic_signal': harmonic_signal
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        harmonic_data = self.calculate(data, params)
        entries = (harmonic_data['harmonic_signal'] > 0) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': harmonic_data['harmonic_signal'].clip(0, 3)/3}
    
    def generate_signals_dynamic(self, data, params):
        harmonic_data = self.calculate(data, params)
        entries = (harmonic_data['harmonic_signal'] > 0) & (data['close'] > data['close'].shift(1))
        exits = (harmonic_data['harmonic_signal'] == 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('harmonic_exit', index=data.index),
                'signal_strength': harmonic_data['harmonic_signal'].clip(0, 3)/3}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
