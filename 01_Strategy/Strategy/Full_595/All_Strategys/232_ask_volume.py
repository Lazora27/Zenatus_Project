"""232 - Ask Volume"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AskVolume:
    """Ask Volume - Estimated Ask Side Volume"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AskVolume", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        close, volume = data['close'], data['volume']
        
        # Ask Volume Approximation (volume on up moves)
        price_up = (close > close.shift(1)).astype(int)
        ask_volume = price_up * volume
        
        # Ask Volume MA
        ask_vol_ma = ask_volume.rolling(period).mean()
        
        # Cumulative Ask Volume
        cumulative_ask = ask_volume.rolling(period).sum()
        
        # Ask Volume Ratio
        total_volume = volume.rolling(period).sum()
        ask_ratio = cumulative_ask / (total_volume + 1e-10)
        
        # High Ask Volume
        high_ask = (ask_volume > ask_vol_ma * 1.5).astype(int)
        
        # Ask Pressure
        ask_pressure = cumulative_ask / (period + 1e-10)
        
        # Ask Dominance
        ask_dominance = (ask_ratio > 0.6).astype(int)
        
        return pd.DataFrame({
            'ask_volume': ask_volume,
            'ask_vol_ma': ask_vol_ma,
            'cumulative_ask': cumulative_ask,
            'ask_ratio': ask_ratio,
            'high_ask': high_ask,
            'ask_pressure': ask_pressure,
            'ask_dominance': ask_dominance
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        av_data = self.calculate(data, params)
        entries = (av_data['ask_dominance'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': av_data['ask_ratio']}
    
    def generate_signals_dynamic(self, data, params):
        av_data = self.calculate(data, params)
        entries = (av_data['ask_dominance'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (av_data['ask_ratio'] < 0.4)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('low_ask_pressure', index=data.index),
                'signal_strength': av_data['ask_ratio']}
    
    def get_ml_features(self, data, params):
        av_data = self.calculate(data, params)
        return pd.DataFrame({
            'cumulative_ask': av_data['cumulative_ask'],
            'ask_ratio': av_data['ask_ratio'],
            'high_ask': av_data['high_ask'],
            'ask_pressure': av_data['ask_pressure'],
            'ask_dominance': av_data['ask_dominance']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
