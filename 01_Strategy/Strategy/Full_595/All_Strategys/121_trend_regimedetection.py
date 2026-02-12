"""121 - Regime Detection"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_RegimeDetection:
    """Regime Detection - Hidden Markov Model-inspired regime detector"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [10,14,20,25,30], 'optimize': True},
        'threshold': {'default': 0.6, 'values': [0.5,0.6,0.7,0.8], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "RegimeDetection", "Regime", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 0.6)
        
        # Calculate returns
        returns = data['close'].pct_change()
        
        # Calculate rolling statistics
        mean_return = returns.rolling(period).mean()
        std_return = returns.rolling(period).std()
        
        # Calculate regime probability (trending vs ranging)
        # Trending: high absolute mean, low std
        # Ranging: low absolute mean, high std
        
        trend_score = abs(mean_return) / (std_return + 1e-10)
        trend_prob = 1 / (1 + np.exp(-5 * (trend_score - 0.5)))  # Sigmoid
        
        # Volatility regime
        vol_ma = std_return.rolling(50).mean()
        vol_regime = (std_return > vol_ma).astype(int)  # 0=low, 1=high
        
        # Direction
        direction = (mean_return > 0).astype(int)  # 0=down, 1=up
        
        # Combined regime (0-3)
        # 0: Ranging/Low Vol, 1: Trending Up/Low Vol
        # 2: Ranging/High Vol, 3: Trending Down/High Vol
        regime = pd.Series(0, index=data.index)
        regime = regime.where(~((trend_prob > threshold) & (direction == 1) & (vol_regime == 0)), 1)
        regime = regime.where(~((trend_prob < threshold) & (vol_regime == 1)), 2)
        regime = regime.where(~((trend_prob > threshold) & (direction == 0) & (vol_regime == 1)), 3)
        
        return pd.DataFrame({
            'regime': regime,
            'trend_prob': trend_prob,
            'vol_regime': vol_regime,
            'direction': direction
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        # Entry when regime = 1 (Trending Up/Low Vol)
        entries = (result['regime'] == 1) & (result['regime'].shift(1) != 1)
        
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
                'signal_strength': result['trend_prob']}
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        entries = (result['regime'] == 1) & (result['regime'].shift(1) != 1)
        exits = (result['regime'] != 1) & (result['regime'].shift(1) == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('regime_change', index=data.index),
                'signal_strength': result['trend_prob']}
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        return pd.DataFrame({
            'regime': result['regime'],
            'trend_prob': result['trend_prob'],
            'vol_regime': result['vol_regime'],
            'direction': result['direction'],
            'regime_trending_up': (result['regime'] == 1).astype(int),
            'regime_ranging': ((result['regime'] == 0) | (result['regime'] == 2)).astype(int)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
