"""143 - TTM Squeeze"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_TTMSqueeze:
    """TTM Squeeze - John Carter's squeeze indicator"""
    PARAMETERS = {
        'length': {'default': 20, 'values': [14,20,25,30], 'optimize': True},
        'mult': {'default': 2.0, 'values': [1.5,2.0,2.5], 'optimize': True},
        'length_kc': {'default': 20, 'values': [14,20,25,30], 'optimize': True},
        'mult_kc': {'default': 1.5, 'values': [1.0,1.5,2.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "TTMSqueeze", "Volatility", __version__
    
    def calculate(self, data, params):
        length = params.get('length', 20)
        mult = params.get('mult', 2.0)
        length_kc = params.get('length_kc', 20)
        mult_kc = params.get('mult_kc', 1.5)
        
        # Bollinger Bands
        basis = data['close'].rolling(length).mean()
        dev = data['close'].rolling(length).std() * mult
        upper_bb = basis + dev
        lower_bb = basis - dev
        
        # Keltner Channels
        ma = data['close'].rolling(length_kc).mean()
        range_ma = (data['high'] - data['low']).rolling(length_kc).mean()
        upper_kc = ma + range_ma * mult_kc
        lower_kc = ma - range_ma * mult_kc
        
        # Squeeze
        sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
        sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
        no_sqz = ~sqz_on & ~sqz_off
        
        # Linear regression for momentum
        val = pd.Series(index=data.index, dtype=float)
        for i in range(length, len(data)):
            highest = data['high'].iloc[i-length:i].max()
            lowest = data['low'].iloc[i-length:i].min()
            avg = (highest + lowest) / 2 + ma.iloc[i]
            val.iloc[i] = data['close'].iloc[i] - avg / 2
        
        return pd.DataFrame({
            'sqz_on': sqz_on.astype(int),
            'sqz_off': sqz_off.astype(int),
            'no_sqz': no_sqz.astype(int),
            'val': val.fillna(0)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        ttm = self.calculate(data, params)
        # Entry when squeeze releases (sqz_off) and value is positive
        entries = (ttm['sqz_off'] == 1) & (ttm['val'] > 0)
        
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
                'signal_strength': abs(ttm['val']).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        ttm = self.calculate(data, params)
        entries = (ttm['sqz_off'] == 1) & (ttm['val'] > 0)
        exits = (ttm['val'] < 0) & (ttm['val'].shift(1) >= 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('ttm_negative', index=data.index),
                'signal_strength': abs(ttm['val']).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        ttm = self.calculate(data, params)
        return pd.DataFrame({
            'ttm_sqz_on': ttm['sqz_on'],
            'ttm_sqz_off': ttm['sqz_off'],
            'ttm_no_sqz': ttm['no_sqz'],
            'ttm_val': ttm['val'],
            'ttm_positive': (ttm['val'] > 0).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
