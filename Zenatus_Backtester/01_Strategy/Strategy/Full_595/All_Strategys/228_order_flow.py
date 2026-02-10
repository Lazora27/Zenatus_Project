"""228 - Order Flow"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_OrderFlow:
    """Order Flow - Directional Order Flow Analysis"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "OrderFlow", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        close, volume = data['close'], data['volume']
        
        # Order Flow Direction
        price_change = close.diff()
        flow_direction = np.sign(price_change)
        
        # Directional Volume
        flow_volume = flow_direction * volume
        
        # Cumulative Order Flow
        cumulative_flow = flow_volume.rolling(period).sum()
        
        # Order Flow Strength
        total_volume = volume.rolling(period).sum()
        flow_strength = cumulative_flow / (total_volume + 1e-10)
        
        # Positive/Negative Flow
        positive_flow = (flow_direction > 0).astype(int) * volume
        negative_flow = (flow_direction < 0).astype(int) * volume
        
        # Flow Ratio
        pos_sum = positive_flow.rolling(period).sum()
        neg_sum = negative_flow.rolling(period).sum()
        flow_ratio = pos_sum / (neg_sum + 1e-10)
        
        # Flow Momentum
        flow_momentum = cumulative_flow.diff(period)
        
        # Strong Flow
        strong_positive = (flow_strength > 0.3).astype(int)
        strong_negative = (flow_strength < -0.3).astype(int)
        
        return pd.DataFrame({
            'cumulative_flow': cumulative_flow,
            'flow_strength': flow_strength,
            'flow_ratio': flow_ratio,
            'flow_momentum': flow_momentum,
            'strong_positive': strong_positive,
            'strong_negative': strong_negative
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        of_data = self.calculate(data, params)
        entries = (of_data['strong_positive'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(of_data['flow_strength'])}
    
    def generate_signals_dynamic(self, data, params):
        of_data = self.calculate(data, params)
        entries = (of_data['strong_positive'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (of_data['strong_negative'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('negative_flow', index=data.index),
                'signal_strength': abs(of_data['flow_strength'])}
    
    def get_ml_features(self, data, params):
        of_data = self.calculate(data, params)
        return pd.DataFrame({
            'cumulative_flow': of_data['cumulative_flow'],
            'flow_strength': of_data['flow_strength'],
            'flow_ratio': of_data['flow_ratio'],
            'flow_momentum': of_data['flow_momentum'],
            'strong_positive': of_data['strong_positive']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
