"""123 - Adaptive MACD"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_AdaptiveMACD:
    """Adaptive MACD - MACD with adaptive periods"""
    PARAMETERS = {
        'fast_base': {'default': 12, 'values': [8,10,12,14], 'optimize': True},
        'slow_base': {'default': 26, 'values': [20,24,26,30], 'optimize': True},
        'signal': {'default': 9, 'values': [5,7,9,11], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "AdaptiveMACD", "Momentum", __version__
    
    def calculate(self, data, params):
        fast_base = params.get('fast_base', 12)
        slow_base = params.get('slow_base', 26)
        signal_period = params.get('signal', 9)
        
        # Calculate volatility for adaptation
        returns = data['close'].pct_change()
        volatility = returns.rolling(20).std()
        vol_ratio = volatility / volatility.rolling(100).mean()
        
        # Adaptive periods (faster in high vol, slower in low vol)
        fast_period = (fast_base / vol_ratio).clip(fast_base * 0.5, fast_base * 2)
        slow_period = (slow_base / vol_ratio).clip(slow_base * 0.5, slow_base * 2)
        
        # Calculate adaptive MACD
        macd_line = pd.Series(0.0, index=data.index)
        fast_ema = data['close'].iloc[0]
        slow_ema = data['close'].iloc[0]
        
        for i in range(1, len(data)):
            # Adaptive alpha
            alpha_fast = 2 / (fast_period.iloc[i] + 1) if not np.isnan(fast_period.iloc[i]) else 2 / (fast_base + 1)
            alpha_slow = 2 / (slow_period.iloc[i] + 1) if not np.isnan(slow_period.iloc[i]) else 2 / (slow_base + 1)
            
            fast_ema = alpha_fast * data['close'].iloc[i] + (1 - alpha_fast) * fast_ema
            slow_ema = alpha_slow * data['close'].iloc[i] + (1 - alpha_slow) * slow_ema
            
            macd_line.iloc[i] = fast_ema - slow_ema
        
        # Signal line
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when MACD crosses above signal
        entries = (result['macd'] > result['signal']) & (result['macd'].shift(1) <= result['signal'].shift(1))
        
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
                'signal_strength': abs(result['histogram']).clip(0, 0.01) / 0.01}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['macd'] > result['signal']) & (result['macd'].shift(1) <= result['signal'].shift(1))
        exits = (result['macd'] < result['signal']) & (result['macd'].shift(1) >= result['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('macd_cross', index=data.index),
                'signal_strength': abs(result['histogram']).clip(0, 0.01) / 0.01}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({
            'amacd_line': result['macd'],
            'amacd_signal': result['signal'],
            'amacd_histogram': result['histogram'],
            'amacd_positive': (result['macd'] > 0).astype(int),
            'amacd_divergence': result['macd'] - result['signal']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
