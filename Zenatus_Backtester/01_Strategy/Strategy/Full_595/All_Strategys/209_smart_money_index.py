"""209 - Smart Money Index"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_SmartMoneyIndex:
    """Smart Money Index - Institutional Money Flow"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "SmartMoneyIndex", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        high, low, close, volume = data['high'], data['low'], data['close'], data['volume']
        
        # Intraday Price Change
        intraday_change = close - data['open']
        
        # Smart Money Flow
        # Positive when close > open (buying pressure)
        smart_money_flow = intraday_change * volume
        
        # Cumulative Smart Money Index
        smi = smart_money_flow.cumsum()
        
        # SMI Trend
        smi_ma = smi.rolling(period).mean()
        smi_trend = (smi > smi_ma).astype(int)
        
        # SMI Momentum
        smi_momentum = smi.diff(period)
        
        # SMI Divergence
        price_ma = close.rolling(period).mean()
        price_trend = (close > price_ma).astype(int)
        smi_divergence = (smi_trend != price_trend).astype(int)
        
        # Normalized SMI
        smi_normalized = (smi - smi.rolling(100).min()) / (smi.rolling(100).max() - smi.rolling(100).min() + 1e-10)
        
        return pd.DataFrame({
            'smi': smi,
            'smi_ma': smi_ma,
            'smi_trend': smi_trend,
            'smi_momentum': smi_momentum,
            'smi_divergence': smi_divergence,
            'smi_normalized': smi_normalized
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        smi_data = self.calculate(data, params)
        entries = (smi_data['smi'] > smi_data['smi_ma']) & (smi_data['smi'].shift(1) <= smi_data['smi_ma'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': smi_data['smi_normalized']}
    
    def generate_signals_dynamic(self, data, params):
        smi_data = self.calculate(data, params)
        entries = (smi_data['smi'] > smi_data['smi_ma']) & (smi_data['smi'].shift(1) <= smi_data['smi_ma'].shift(1))
        exits = (smi_data['smi'] < smi_data['smi_ma']) & (smi_data['smi'].shift(1) >= smi_data['smi_ma'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('smi_cross_down', index=data.index),
                'signal_strength': smi_data['smi_normalized']}
    
    def get_ml_features(self, data, params):
        smi_data = self.calculate(data, params)
        return pd.DataFrame({
            'smi_normalized': smi_data['smi_normalized'],
            'smi_trend': smi_data['smi_trend'],
            'smi_momentum': smi_data['smi_momentum'],
            'smi_divergence': smi_data['smi_divergence'],
            'smi_slope': smi_data['smi'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
