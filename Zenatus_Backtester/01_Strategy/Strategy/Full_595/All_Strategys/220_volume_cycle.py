"""220 - Volume Cycle"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeCycle:
    """Volume Cycle - Cyclical Volume Patterns"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'cycle_length': {'default': 10, 'values': [5,7,10,14,20], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeCycle", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        cycle_len = params.get('cycle_length', 10)
        volume = data['volume']
        
        # Detrended Volume
        vol_ma = volume.rolling(period).mean()
        detrended_vol = volume - vol_ma
        
        # Volume Cycle (Simple Moving Average of Detrended)
        vol_cycle = detrended_vol.rolling(cycle_len).mean()
        
        # Cycle Phase
        cycle_positive = (vol_cycle > 0).astype(int)
        
        # Cycle Extremes
        cycle_high = vol_cycle.rolling(period).max()
        cycle_low = vol_cycle.rolling(period).min()
        
        # Cycle Position (0-1)
        cycle_position = (vol_cycle - cycle_low) / (cycle_high - cycle_low + 1e-10)
        
        # Cycle Turning Points
        cycle_peak = (vol_cycle > vol_cycle.shift(1)) & (vol_cycle > vol_cycle.shift(-1))
        cycle_trough = (vol_cycle < vol_cycle.shift(1)) & (vol_cycle < vol_cycle.shift(-1))
        
        # Cycle Strength
        cycle_amplitude = cycle_high - cycle_low
        cycle_strength = cycle_amplitude / (vol_ma + 1e-10)
        
        return pd.DataFrame({
            'vol_cycle': vol_cycle,
            'cycle_position': cycle_position,
            'cycle_positive': cycle_positive,
            'cycle_peak': cycle_peak.astype(int),
            'cycle_trough': cycle_trough.astype(int),
            'cycle_strength': cycle_strength
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vc_data = self.calculate(data, params)
        # Entry bei Cycle Trough (Low Volume Cycle)
        entries = (vc_data['cycle_trough'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vc_data['cycle_position']}
    
    def generate_signals_dynamic(self, data, params):
        vc_data = self.calculate(data, params)
        entries = (vc_data['cycle_trough'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (vc_data['cycle_peak'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cycle_peak', index=data.index),
                'signal_strength': vc_data['cycle_position']}
    
    def get_ml_features(self, data, params):
        vc_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_cycle': vc_data['vol_cycle'],
            'cycle_position': vc_data['cycle_position'],
            'cycle_positive': vc_data['cycle_positive'],
            'cycle_peak': vc_data['cycle_peak'],
            'cycle_trough': vc_data['cycle_trough'],
            'cycle_strength': vc_data['cycle_strength']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
