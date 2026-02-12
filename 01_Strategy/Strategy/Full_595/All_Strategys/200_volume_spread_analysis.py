"""200 - Volume Spread Analysis"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeSpreadAnalysis:
    """Volume Spread Analysis - VSA Methodology"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [13,17,19,20,21,23,25,29], 'optimize': True},
        'vol_threshold': {'default': 1.5, 'values': [1.2,1.5,1.8,2.0,2.5], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeSpreadAnalysis", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        vol_threshold = params.get('vol_threshold', 1.5)
        
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Spread (Range)
        spread = high - low
        avg_spread = spread.rolling(period).mean()
        
        # Volume analysis
        avg_volume = volume.rolling(period).mean()
        vol_ratio = volume / (avg_volume + 1e-10)
        
        # High volume detection
        high_volume = (vol_ratio > vol_threshold).astype(int)
        low_volume = (vol_ratio < 1 / vol_threshold).astype(int)
        
        # Spread analysis
        wide_spread = (spread > avg_spread * 1.5).astype(int)
        narrow_spread = (spread < avg_spread * 0.5).astype(int)
        
        # Close position in range
        close_position = (close - low) / (spread + 1e-10)
        
        # VSA Signals
        # No Demand: High volume + narrow spread + close in middle
        no_demand = (high_volume == 1) & (narrow_spread == 1) & (close_position > 0.4) & (close_position < 0.6)
        
        # Stopping Volume: High volume + wide spread + close near high
        stopping_volume = (high_volume == 1) & (wide_spread == 1) & (close_position > 0.7)
        
        # Effort vs Result
        effort = vol_ratio * spread
        result = abs(close - close.shift(1))
        effort_result_ratio = effort / (result + 1e-10)
        
        return pd.DataFrame({
            'spread': spread,
            'vol_ratio': vol_ratio,
            'close_position': close_position,
            'high_volume': high_volume,
            'low_volume': low_volume,
            'wide_spread': wide_spread,
            'narrow_spread': narrow_spread,
            'no_demand': no_demand.astype(int),
            'stopping_volume': stopping_volume.astype(int),
            'effort_result_ratio': effort_result_ratio
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vsa_data = self.calculate(data, params)
        
        # Entry on stopping volume (potential reversal)
        entries = (vsa_data['stopping_volume'] == 1) & (data['close'] > data['close'].shift(1))
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vsa_data['close_position']}
    
    def generate_signals_dynamic(self, data, params):
        vsa_data = self.calculate(data, params)
        
        entries = (vsa_data['stopping_volume'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (vsa_data['no_demand'] == 1)
        
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('no_demand', index=data.index),
                'signal_strength': vsa_data['close_position']}
    
    def get_ml_features(self, data, params):
        vsa_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_ratio': vsa_data['vol_ratio'],
            'close_position': vsa_data['close_position'],
            'high_volume': vsa_data['high_volume'],
            'wide_spread': vsa_data['wide_spread'],
            'no_demand': vsa_data['no_demand'],
            'stopping_volume': vsa_data['stopping_volume'],
            'effort_result_ratio': vsa_data['effort_result_ratio']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
