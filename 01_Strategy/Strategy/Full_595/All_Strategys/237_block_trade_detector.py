"""237 - Block Trade Detector"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_BlockTradeDetector:
    """Block Trade Detector - Identifies Block Trades (Very Large Orders)"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,30,50], 'optimize': True},
        'threshold': {'default': 3.0, 'values': [2.5,3.0,3.5,4.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "BlockTradeDetector", "Tick_Trade", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 3.0)
        volume = data['volume']
        
        # Volume Statistics
        vol_ma = volume.rolling(period).mean()
        vol_std = volume.rolling(period).std()
        vol_zscore = (volume - vol_ma) / (vol_std + 1e-10)
        
        # Block Trade Detection (even larger than large trades)
        block_trade = (vol_zscore > threshold).astype(int)
        
        # Block Trade with Price Impact
        price_change = abs(data['close'].pct_change())
        block_with_impact = (block_trade == 1) & (price_change > price_change.rolling(period).mean())
        
        # Block Trade Frequency
        block_freq = block_trade.rolling(period).sum()
        
        # Block Trade Intensity
        block_intensity = (volume * block_trade) / (vol_ma + 1e-10)
        
        return pd.DataFrame({
            'vol_zscore': vol_zscore,
            'block_trade': block_trade,
            'block_with_impact': block_with_impact.astype(int),
            'block_freq': block_freq,
            'block_intensity': block_intensity
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        btd_data = self.calculate(data, params)
        entries = (btd_data['block_with_impact'] == 1) & (data['close'] > data['close'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': btd_data['block_intensity'].clip(0, 10)/10}
    
    def generate_signals_dynamic(self, data, params):
        btd_data = self.calculate(data, params)
        entries = (btd_data['block_with_impact'] == 1) & (data['close'] > data['close'].shift(1))
        exits = (btd_data['vol_zscore'] < 1.0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('volume_normalized', index=data.index),
                'signal_strength': btd_data['block_intensity'].clip(0, 10)/10}
    
    def get_ml_features(self, data, params):
        btd_data = self.calculate(data, params)
        return pd.DataFrame({
            'vol_zscore': btd_data['vol_zscore'],
            'block_trade': btd_data['block_trade'],
            'block_with_impact': btd_data['block_with_impact'],
            'block_freq': btd_data['block_freq'],
            'block_intensity': btd_data['block_intensity']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
