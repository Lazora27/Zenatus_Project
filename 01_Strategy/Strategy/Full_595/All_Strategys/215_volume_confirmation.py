"""215 - Volume Confirmation"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeConfirmation:
    """Volume Confirmation - Volume Validates Price Moves"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'vol_threshold': {'default': 1.2, 'values': [1.0,1.2,1.5,1.8,2.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeConfirmation", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        vol_threshold = params.get('vol_threshold', 1.2)
        
        close, volume = data['close'], data['volume']
        
        # Price Movement
        price_up = (close > close.shift(1)).astype(int)
        price_down = (close < close.shift(1)).astype(int)
        
        # Volume Analysis
        vol_ma = volume.rolling(period).mean()
        high_volume = (volume > vol_ma * vol_threshold).astype(int)
        
        # Confirmed Moves
        confirmed_up = (price_up == 1) & (high_volume == 1)
        confirmed_down = (price_down == 1) & (high_volume == 1)
        
        # Unconfirmed Moves (weak)
        unconfirmed_up = (price_up == 1) & (high_volume == 0)
        unconfirmed_down = (price_down == 1) & (high_volume == 0)
        
        # Confirmation Strength
        vol_ratio = volume / vol_ma
        confirmation_strength = vol_ratio * abs(close.pct_change())
        
        # Confirmation Streak
        confirmed_streak = confirmed_up.rolling(3).sum()
        
        return pd.DataFrame({
            'confirmed_up': confirmed_up.astype(int),
            'confirmed_down': confirmed_down.astype(int),
            'unconfirmed_up': unconfirmed_up.astype(int),
            'unconfirmed_down': unconfirmed_down.astype(int),
            'confirmation_strength': confirmation_strength,
            'confirmed_streak': confirmed_streak,
            'vol_ratio': vol_ratio
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vc_data = self.calculate(data, params)
        entries = (vc_data['confirmed_up'] == 1)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vc_data['confirmation_strength'].clip(0, 5)/5}
    
    def generate_signals_dynamic(self, data, params):
        vc_data = self.calculate(data, params)
        entries = (vc_data['confirmed_up'] == 1)
        exits = (vc_data['unconfirmed_up'] == 1) | (vc_data['confirmed_down'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('unconfirmed_move', index=data.index),
                'signal_strength': vc_data['confirmation_strength'].clip(0, 5)/5}
    
    def get_ml_features(self, data, params):
        vc_data = self.calculate(data, params)
        return pd.DataFrame({
            'confirmed_up': vc_data['confirmed_up'],
            'confirmed_down': vc_data['confirmed_down'],
            'unconfirmed_up': vc_data['unconfirmed_up'],
            'confirmation_strength': vc_data['confirmation_strength'],
            'confirmed_streak': vc_data['confirmed_streak'],
            'vol_ratio': vc_data['vol_ratio']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
