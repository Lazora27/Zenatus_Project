"""095 - MFI Extended (Money Flow Index with Divergence)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_MFIExtended:
    """MFI Extended - Money Flow Index with enhanced features"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [5,7,8,11,13,14,17,19,21], 'optimize': True},
        'overbought': {'default': 80, 'values': [70,75,80,85], 'optimize': True},
        'oversold': {'default': 20, 'values': [15,20,25,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "MFIExtended", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        # Typical Price
        tp = (data['high'] + data['low'] + data['close']) / 3
        
        # Raw Money Flow
        mf = tp * data['volume']
        
        # Positive and Negative Money Flow
        pos_mf = mf.where(tp > tp.shift(1), 0)
        neg_mf = mf.where(tp < tp.shift(1), 0)
        
        # Money Flow Ratio
        pos_mf_sum = pos_mf.rolling(period).sum()
        neg_mf_sum = neg_mf.rolling(period).sum()
        
        mfr = pos_mf_sum / (neg_mf_sum + 1e-10)
        
        # MFI
        mfi = (100 - (100 / (1 + mfr))).fillna(50)
        
        return mfi
    
    def generate_signals_fixed(self, data, params):
        mfi = self.calculate(data, params)
        oversold = params.get('oversold', 20)
        
        # Entry when MFI crosses above oversold level
        entries = (mfi > oversold) & (mfi.shift(1) <= oversold)
        
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
                'signal_strength': abs(mfi - 50) / 50}
    
    def generate_signals_dynamic(self, data, params):
        mfi = self.calculate(data, params)
        oversold = params.get('oversold', 20)
        overbought = params.get('overbought', 80)
        
        entries = (mfi > oversold) & (mfi.shift(1) <= oversold)
        exits = (mfi > overbought) & (mfi.shift(1) <= overbought)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('mfi_overbought', index=data.index),
                'signal_strength': abs(mfi - 50) / 50}
    
    def get_ml_features(self, data, params):
        mfi = self.calculate(data, params)
        overbought = params.get('overbought', 80)
        oversold = params.get('oversold', 20)
        
        return pd.DataFrame({'mfi_value': mfi, 'mfi_slope': mfi.diff(),
                           'mfi_overbought': (mfi > overbought).astype(int),
                           'mfi_oversold': (mfi < oversold).astype(int),
                           'mfi_divergence': mfi - mfi.rolling(14).mean()}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
