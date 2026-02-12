"""218 - Volume Pressure"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumePressure:
    """Volume Pressure - Buying/Selling Pressure Analysis"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumePressure", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Buying/Selling Pressure
        close_position = (close - low) / (high - low + 1e-10)
        buying_pressure = close_position * volume
        selling_pressure = (1 - close_position) * volume
        
        # Net Pressure
        net_pressure = buying_pressure - selling_pressure
        
        # Cumulative Pressure
        cumulative_pressure = net_pressure.rolling(period).sum()
        
        # Pressure Ratio
        total_buying = buying_pressure.rolling(period).sum()
        total_selling = selling_pressure.rolling(period).sum()
        pressure_ratio = total_buying / (total_selling + 1e-10)
        
        # Pressure Trend
        pressure_ma = cumulative_pressure.rolling(period).mean()
        pressure_trend = (cumulative_pressure > pressure_ma).astype(int)
        
        # Extreme Pressure
        buying_extreme = (pressure_ratio > 2.0).astype(int)
        selling_extreme = (pressure_ratio < 0.5).astype(int)
        
        return pd.DataFrame({
            'buying_pressure': buying_pressure,
            'selling_pressure': selling_pressure,
            'net_pressure': net_pressure,
            'cumulative_pressure': cumulative_pressure,
            'pressure_ratio': pressure_ratio,
            'pressure_trend': pressure_trend,
            'buying_extreme': buying_extreme,
            'selling_extreme': selling_extreme
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vp_data = self.calculate(data, params)
        entries = (vp_data['cumulative_pressure'] > 0) & (vp_data['cumulative_pressure'].shift(1) <= 0)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vp_data['pressure_ratio'].clip(0, 3)/3}
    
    def generate_signals_dynamic(self, data, params):
        vp_data = self.calculate(data, params)
        entries = (vp_data['cumulative_pressure'] > 0) & (vp_data['cumulative_pressure'].shift(1) <= 0)
        exits = (vp_data['cumulative_pressure'] < 0) & (vp_data['cumulative_pressure'].shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('selling_pressure', index=data.index),
                'signal_strength': vp_data['pressure_ratio'].clip(0, 3)/3}
    
    def get_ml_features(self, data, params):
        vp_data = self.calculate(data, params)
        return pd.DataFrame({
            'net_pressure': vp_data['net_pressure'],
            'cumulative_pressure': vp_data['cumulative_pressure'],
            'pressure_ratio': vp_data['pressure_ratio'],
            'pressure_trend': vp_data['pressure_trend'],
            'buying_extreme': vp_data['buying_extreme'],
            'selling_extreme': vp_data['selling_extreme']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
