"""284 - Fibonacci Time Zones"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_FibonacciTimeZones:
    """Fibonacci Time Zones - Time-Based Reversal Points"""
    PARAMETERS = {
        'start_index': {'default': 0, 'values': [0,10,20], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "FibonacciTimeZones", "Patterns", __version__
    
    def calculate(self, data, params):
        start_index = params.get('start_index', 0)
        
        # Fibonacci sequence for time zones
        fib_sequence = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
        
        # Create time zone markers
        time_zones = pd.Series(0, index=data.index)
        
        for i, fib_num in enumerate(fib_sequence):
            zone_index = start_index + fib_num
            if zone_index < len(data):
                # Mark a window around the Fibonacci time
                for offset in range(-2, 3):
                    idx = zone_index + offset
                    if 0 <= idx < len(data):
                        time_zones.iloc[idx] = i + 1
        
        # Time zone strength (higher for later Fibonacci numbers)
        time_zone_strength = time_zones / max(fib_sequence)
        
        # Reversal probability at time zones
        reversal_signal = (time_zones > 0).astype(int)
        
        return pd.DataFrame({
            'time_zones': time_zones,
            'time_zone_strength': time_zone_strength,
            'reversal_signal': reversal_signal
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        tz_data = self.calculate(data, params)
        entries = (tz_data['reversal_signal'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': tz_data['time_zone_strength']}
    
    def generate_signals_dynamic(self, data, params):
        tz_data = self.calculate(data, params)
        entries = (tz_data['reversal_signal'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (tz_data['reversal_signal'].shift(-5) == 1)  # Exit at next time zone
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('next_time_zone', index=data.index),
                'signal_strength': tz_data['time_zone_strength']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
