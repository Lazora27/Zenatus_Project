"""102 - Connors RSI"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_ConnorsRSI:
    """Connors RSI - Composite momentum indicator"""
    PARAMETERS = {
        'rsi_period': {'default': 3, 'values': [2,3,5,7], 'optimize': True},
        'streak_period': {'default': 2, 'values': [2,3,5], 'optimize': True},
        'pct_rank_period': {'default': 100, 'values': [50,100,200], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "ConnorsRSI", "Momentum", __version__
    
    def calculate(self, data, params):
        rsi_period = params.get('rsi_period', 3)
        streak_period = params.get('streak_period', 2)
        pct_rank_period = params.get('pct_rank_period', 100)
        
        # Component 1: Short-term RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
        avg_loss = loss.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Component 2: Streak RSI
        streak = pd.Series(0, index=data.index)
        current_streak = 0
        for i in range(1, len(data)):
            if data['close'].iloc[i] > data['close'].iloc[i-1]:
                current_streak = max(1, current_streak + 1)
            elif data['close'].iloc[i] < data['close'].iloc[i-1]:
                current_streak = min(-1, current_streak - 1)
            else:
                current_streak = 0
            streak.iloc[i] = current_streak
        
        # RSI of streak
        streak_delta = pd.Series(streak, index=data.index)
        streak_gain = streak_delta.where(streak_delta > 0, 0)
        streak_loss = -streak_delta.where(streak_delta < 0, 0)
        streak_avg_gain = streak_gain.ewm(alpha=1/streak_period, min_periods=streak_period).mean()
        streak_avg_loss = streak_loss.ewm(alpha=1/streak_period, min_periods=streak_period).mean()
        streak_rs = streak_avg_gain / (streak_avg_loss + 1e-10)
        streak_rsi = 100 - (100 / (1 + streak_rs))
        
        # Component 3: Percent Rank
        roc = data['close'].pct_change()
        pct_rank = roc.rolling(pct_rank_period).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x) * 100, raw=False)
        
        # Connors RSI = Average of 3 components
        crsi = (rsi + streak_rsi + pct_rank) / 3
        
        return crsi.fillna(50)
    
    def generate_signals_fixed(self, data, params):
        crsi = self.calculate(data, params)
        # Entry when crosses above 20 (oversold)
        entries = (crsi > 20) & (crsi.shift(1) <= 20)
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(crsi - 50) / 50}
    
    def generate_signals_dynamic(self, data, params):
        crsi = self.calculate(data, params)
        entries = (crsi > 20) & (crsi.shift(1) <= 20)
        exits = (crsi > 80) & (crsi.shift(1) <= 80)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('crsi_overbought', index=data.index),
                'signal_strength': abs(crsi - 50) / 50}
    
    def get_ml_features(self, data, params):
        crsi = self.calculate(data, params)
        return pd.DataFrame({'crsi_value': crsi, 'crsi_slope': crsi.diff(),
                           'crsi_overbought': (crsi > 80).astype(int),
                           'crsi_oversold': (crsi < 20).astype(int)}, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
