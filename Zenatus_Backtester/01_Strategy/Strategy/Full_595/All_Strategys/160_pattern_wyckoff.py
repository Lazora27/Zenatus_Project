"""160 - Wyckoff Method"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Wyckoff:
    """Wyckoff Method - Accumulation/Distribution phases"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [14,20,30,40], 'optimize': True},
        'volume_threshold': {'default': 1.5, 'values': [1.2,1.5,2.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "Wyckoff", "Pattern", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        vol_threshold = params.get('volume_threshold', 1.5)
        
        # Price and volume analysis
        price_range = data['high'] - data['low']
        
        # Volume (use close if volume not available)
        if 'volume' in data.columns:
            volume = data['volume']
        else:
            volume = abs(data['close'].diff()) * 1000  # Proxy volume
        
        volume_ma = volume.rolling(period).mean()
        
        # Wyckoff phases
        phases = pd.DataFrame(index=data.index)
        
        # 1. Spring (accumulation): Low volume, narrow range at support
        support = data['low'].rolling(period).min()
        at_support = abs(data['low'] - support) < price_range * 0.1
        low_volume = volume < volume_ma * 0.8
        narrow_range = price_range < price_range.rolling(period).mean() * 0.8
        
        phases['spring'] = (at_support & low_volume & narrow_range).astype(int)
        
        # 2. Sign of Strength (SOS): High volume breakout
        resistance = data['high'].rolling(period).max()
        breakout = data['close'] > resistance.shift(1)
        high_volume = volume > volume_ma * vol_threshold
        
        phases['sos'] = (breakout & high_volume).astype(int)
        
        # 3. Last Point of Support (LPS): Pullback on low volume
        pullback = (data['close'] < data['close'].shift(5)) & (data['close'] > support * 1.02)
        
        phases['lps'] = (pullback & low_volume).astype(int)
        
        # 4. Upthrust (distribution): High volume at resistance
        at_resistance = abs(data['high'] - resistance) < price_range * 0.1
        
        phases['upthrust'] = (at_resistance & high_volume & (data['close'] < data['open'])).astype(int)
        
        # 5. Sign of Weakness (SOW): Breakdown on high volume
        breakdown = data['close'] < support.shift(1)
        
        phases['sow'] = (breakdown & high_volume).astype(int)
        
        # Composite Wyckoff score
        accumulation_score = phases['spring'] + phases['sos'] + phases['lps']
        distribution_score = phases['upthrust'] + phases['sow']
        
        wyckoff_signal = accumulation_score - distribution_score
        
        return pd.DataFrame({
            'signal': wyckoff_signal,
            'accumulation': accumulation_score,
            'distribution': distribution_score,
            **phases
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        wyckoff = self.calculate(data, params)
        # Entry on accumulation signals
        entries = (wyckoff['signal'] > 0)
        
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
                'signal_strength': abs(wyckoff['signal']).clip(0, 3) / 3}
    
    def generate_signals_dynamic(self, data, params):
        wyckoff = self.calculate(data, params)
        entries = (wyckoff['signal'] > 0)
        exits = (wyckoff['signal'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('distribution', index=data.index),
                'signal_strength': abs(wyckoff['signal']).clip(0, 3) / 3}
    
    def get_ml_features(self, data, params):
        wyckoff = self.calculate(data, params)
        return pd.DataFrame({
            'wyckoff_signal': wyckoff['signal'],
            'wyckoff_spring': wyckoff['spring'],
            'wyckoff_sos': wyckoff['sos'],
            'wyckoff_lps': wyckoff['lps'],
            'wyckoff_upthrust': wyckoff['upthrust'],
            'wyckoff_accumulation': (wyckoff['accumulation'] > 0).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
