"""151 - Divergence Strength Index"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DivergenceStrength:
    """Divergence Strength Index - Quantifies divergence strength"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [10,14,20,25], 'optimize': True},
        'lookback': {'default': 20, 'values': [14,20,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DivergenceStrength", "Divergence", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        lookback = params.get('lookback', 20)
        
        # Calculate RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate price and RSI slopes
        price_slope = data['close'].diff(lookback)
        rsi_slope = rsi.diff(lookback)
        
        # Divergence strength = difference in normalized slopes
        price_norm = (price_slope - price_slope.rolling(100).mean()) / (price_slope.rolling(100).std() + 1e-10)
        rsi_norm = (rsi_slope - rsi_slope.rolling(100).mean()) / (rsi_slope.rolling(100).std() + 1e-10)
        
        # Strength: positive when diverging
        strength = (rsi_norm - price_norm).fillna(0)
        
        # Smoothed strength
        strength_smooth = strength.rolling(5).mean()
        
        return pd.DataFrame({
            'strength': strength_smooth.fillna(0),
            'raw_strength': strength,
            'rsi': rsi.fillna(50)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        div = self.calculate(data, params)
        # Entry when strength is high (strong bullish divergence)
        entries = (div['strength'] > 1.0) & (div['strength'].shift(1) <= 1.0)
        
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
                'signal_strength': abs(div['strength']).clip(0, 3) / 3}
    
    def generate_signals_dynamic(self, data, params):
        div = self.calculate(data, params)
        entries = (div['strength'] > 1.0) & (div['strength'].shift(1) <= 1.0)
        exits = (div['strength'] < -1.0) & (div['strength'].shift(1) >= -1.0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('strength_negative', index=data.index),
                'signal_strength': abs(div['strength']).clip(0, 3) / 3}
    
    def get_ml_features(self, data, params):
        div = self.calculate(data, params)
        return pd.DataFrame({
            'div_strength': div['strength'],
            'div_raw': div['raw_strength'],
            'div_strong_bull': (div['strength'] > 1.0).astype(int),
            'div_strong_bear': (div['strength'] < -1.0).astype(int),
            'div_slope': div['strength'].diff()
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
