"""154 - Garman-Klass Volatility"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_GarmanKlassVolatility:
    """Garman-Klass Volatility - OHLC Based Estimator"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'annualize': {'default': 252, 'values': [252], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "GarmanKlassVolatility", "Volatility", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        annualize = params.get('annualize', 252)
        
        high, low, open_price, close = data['high'], data['low'], data['open'], data['close']
        
        # Garman-Klass Volatility
        # GK = sqrt(0.5 * (ln(H/L))^2 - (2*ln(2)-1) * (ln(C/O))^2)
        hl_ratio = np.log(high / low)
        co_ratio = np.log(close / open_price)
        
        gk_var = 0.5 * (hl_ratio ** 2) - (2 * np.log(2) - 1) * (co_ratio ** 2)
        gk_vol = np.sqrt(gk_var.rolling(period).mean()) * np.sqrt(annualize) * 100
        
        # Percentile rank
        vol_rank = gk_vol.rolling(100).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # Moving average
        vol_ma = gk_vol.rolling(period).mean()
        
        return pd.DataFrame({
            'gk_vol': gk_vol,
            'vol_rank': vol_rank,
            'vol_ma': vol_ma
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vol_data = self.calculate(data, params)
        
        # Entry when volatility is low and rising
        entries = (vol_data['vol_rank'] < 0.3) & (vol_data['gk_vol'] > vol_data['gk_vol'].shift(1))
        
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        
        signal_strength = (1 - vol_data['vol_rank']).clip(0, 1)
        
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': signal_strength}
    
    def generate_signals_dynamic(self, data, params):
        vol_data = self.calculate(data, params)
        entries = (vol_data['vol_rank'] < 0.3) & (vol_data['gk_vol'] > vol_data['gk_vol'].shift(1))
        exits = (vol_data['vol_rank'] > 0.7) & (vol_data['gk_vol'] < vol_data['gk_vol'].shift(1))
        signal_strength = (1 - vol_data['vol_rank']).clip(0, 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('high_gk_vol', index=data.index),
                'signal_strength': signal_strength}
    
    def get_ml_features(self, data, params):
        vol_data = self.calculate(data, params)
        return pd.DataFrame({
            'gk_vol': vol_data['gk_vol'],
            'gk_rank': vol_data['vol_rank'],
            'gk_slope': vol_data['gk_vol'].diff(),
            'gk_zscore': (vol_data['gk_vol'] - vol_data['vol_ma']) / (vol_data['gk_vol'].rolling(20).std() + 1e-10)
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
