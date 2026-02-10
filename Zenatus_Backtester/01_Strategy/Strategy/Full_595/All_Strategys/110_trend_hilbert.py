"""110 - Hilbert Transform Dominant Cycle Period"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HilbertTransform:
    """Hilbert Transform - Dominant Cycle Period"""
    PARAMETERS = {
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HilbertTransform", "Cycle", __version__
    
    def calculate(self, data, params):
        # Detrend price
        detrend = pd.Series(0.0, index=data.index)
        for i in range(7, len(data)):
            detrend.iloc[i] = (0.0962 * data['close'].iloc[i] + 0.5769 * data['close'].iloc[i-2] - 
                             0.5769 * data['close'].iloc[i-4] - 0.0962 * data['close'].iloc[i-6])
        
        # Compute InPhase and Quadrature components
        inphase = pd.Series(0.0, index=data.index)
        quadrature = pd.Series(0.0, index=data.index)
        
        for i in range(7, len(data)):
            inphase.iloc[i] = 1.25 * (detrend.iloc[i-4] - 0.75 * detrend.iloc[i-6])
            quadrature.iloc[i] = detrend.iloc[i-2] - 0.75 * detrend.iloc[i-4]
        
        # Smooth InPhase and Quadrature
        smooth_inphase = inphase.rolling(3).mean()
        smooth_quadrature = quadrature.rolling(3).mean()
        
        # Compute Phase
        phase = pd.Series(0.0, index=data.index)
        for i in range(len(data)):
            if smooth_inphase.iloc[i] != 0:
                phase.iloc[i] = np.arctan(smooth_quadrature.iloc[i] / smooth_inphase.iloc[i])
        
        # Compute Delta Phase
        delta_phase = phase.diff()
        
        # Compute Instantaneous Period
        inst_period = pd.Series(0.0, index=data.index)
        for i in range(len(data)):
            if abs(delta_phase.iloc[i]) > 0.1:
                inst_period.iloc[i] = 2 * np.pi / abs(delta_phase.iloc[i])
            else:
                inst_period.iloc[i] = inst_period.iloc[i-1] if i > 0 else 15
        
        # Dominant Cycle Period (smoothed)
        dc_period = inst_period.rolling(5).median().fillna(15).clip(6, 50)
        
        return dc_period
    
    def generate_signals_fixed(self, data, params):
        dc_period = self.calculate(data, params)
        # Entry when cycle period is increasing (trend strengthening)
        entries = (dc_period > dc_period.shift(1)) & (dc_period.shift(1) <= dc_period.shift(2))
        
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
                'signal_strength': (dc_period - 6) / 44}  # Normalize to 0-1
    
    def generate_signals_dynamic(self, data, params):
        dc_period = self.calculate(data, params)
        entries = (dc_period > dc_period.shift(1)) & (dc_period.shift(1) <= dc_period.shift(2))
        exits = (dc_period < dc_period.shift(1)) & (dc_period.shift(1) >= dc_period.shift(2))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('cycle_weakening', index=data.index),
                'signal_strength': (dc_period - 6) / 44}
    
    def get_ml_features(self, data, params):
        dc_period = self.calculate(data, params)
        return pd.DataFrame({'dc_period': dc_period, 'dc_period_change': dc_period.diff(),
                           'dc_period_short': (dc_period < 15).astype(int),
                           'dc_period_long': (dc_period > 30).astype(int),
                           'dc_period_trend': dc_period.rolling(5).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else 0)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
