"""153 - Divergence Momentum"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_DivergenceMomentum:
    """Divergence Momentum - Momentum-based divergence indicator"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [10,14,20,25], 'optimize': True},
        'lookback': {'default': 20, 'values': [14,20,30,40], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "DivergenceMomentum", "Divergence", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        lookback = params.get('lookback', 20)
        
        # Price momentum
        price_mom = data['close'].diff(period)
        
        # RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        rsi_mom = rsi.diff(period)
        
        # Divergence momentum = RSI momentum - Price momentum (normalized)
        price_mom_norm = (price_mom - price_mom.rolling(100).mean()) / (price_mom.rolling(100).std() + 1e-10)
        rsi_mom_norm = (rsi_mom - rsi_mom.rolling(100).mean()) / (rsi_mom.rolling(100).std() + 1e-10)
        
        div_momentum = (rsi_mom_norm - price_mom_norm).fillna(0)
        
        # Signal line
        signal = div_momentum.rolling(5).mean()
        
        return pd.DataFrame({
            'momentum': div_momentum,
            'signal': signal.fillna(0),
            'histogram': (div_momentum - signal).fillna(0)
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        div = self.calculate(data, params)
        # Entry when momentum crosses above signal
        entries = (div['momentum'] > div['signal']) & (div['momentum'].shift(1) <= div['signal'].shift(1))
        
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
                'signal_strength': abs(div['histogram']).clip(0, 2) / 2}
    
    def generate_signals_dynamic(self, data, params):
        div = self.calculate(data, params)
        entries = (div['momentum'] > div['signal']) & (div['momentum'].shift(1) <= div['signal'].shift(1))
        exits = (div['momentum'] < div['signal']) & (div['momentum'].shift(1) >= div['signal'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('mom_cross', index=data.index),
                'signal_strength': abs(div['histogram']).clip(0, 2) / 2}
    
    def get_ml_features(self, data, params):
        div = self.calculate(data, params)
        return pd.DataFrame({
            'div_mom': div['momentum'],
            'div_mom_signal': div['signal'],
            'div_mom_hist': div['histogram'],
            'div_mom_positive': (div['momentum'] > 0).astype(int),
            'div_mom_above_signal': (div['momentum'] > div['signal']).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
