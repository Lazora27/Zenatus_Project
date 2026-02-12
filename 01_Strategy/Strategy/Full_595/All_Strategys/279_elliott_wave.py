"""279 - Elliott Wave"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ElliottWave:
    """Elliott Wave - Wave Pattern Detection"""
    PARAMETERS = {
        'period': {'default': 50, 'values': [30,50,100], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ElliottWave", "Patterns", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 50)
        high, low, close = data['high'], data['low'], data['close']
        
        # Simplified Elliott Wave detection using zigzag
        # Find swing points
        swing_high = (high > high.shift(1)) & (high > high.shift(-1))
        swing_low = (low < low.shift(1)) & (low < low.shift(-1))
        
        # Wave count approximation
        wave_direction = pd.Series(0, index=data.index)
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                wave_direction.iloc[i] = 1  # Up wave
            elif close.iloc[i] < close.iloc[i-1]:
                wave_direction.iloc[i] = -1  # Down wave
        
        # Wave momentum
        wave_momentum = close.diff().rolling(period).sum()
        
        # Impulse wave (strong directional move)
        impulse_wave = (abs(wave_momentum) > abs(wave_momentum).rolling(period*2).mean() * 1.5).astype(int)
        
        # Corrective wave (consolidation)
        corrective_wave = (abs(wave_momentum) < abs(wave_momentum).rolling(period*2).mean() * 0.5).astype(int)
        
        # Wave 3 detection (strongest wave)
        wave_strength = abs(close.diff().rolling(10).sum())
        wave_3 = (wave_strength > wave_strength.rolling(period).quantile(0.8)).astype(int)
        
        # Wave 5 detection (final wave)
        wave_5 = (impulse_wave == 1) & (wave_3.shift(period//2) == 1)
        wave_5 = wave_5.astype(int)
        
        return pd.DataFrame({
            'wave_direction': wave_direction,
            'wave_momentum': wave_momentum,
            'impulse_wave': impulse_wave,
            'corrective_wave': corrective_wave,
            'wave_3': wave_3,
            'wave_5': wave_5
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        ew_data = self.calculate(data, params)
        entries = (ew_data['wave_3'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': ew_data['impulse_wave']}
    
    def generate_signals_dynamic(self, data, params):
        ew_data = self.calculate(data, params)
        entries = (ew_data['wave_3'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (ew_data['wave_5'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('wave_5_complete', index=data.index),
                'signal_strength': ew_data['impulse_wave']}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
