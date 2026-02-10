"""214 - Volume Divergence"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_VolumeDivergence:
    """Volume Divergence - Price/Volume Disagreement"""
    PARAMETERS = {
        'period': {'default': 14, 'values': [7,10,14,20,30], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "VolumeDivergence", "Volume", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 14)
        
        close, volume = data['close'], data['volume']
        
        # Price Trend
        price_ma = close.rolling(period).mean()
        price_trend = (close > price_ma).astype(int)
        
        # Volume Trend
        vol_ma = volume.rolling(period).mean()
        vol_trend = (volume > vol_ma).astype(int)
        
        # Divergence Detection
        bullish_divergence = (price_trend == 0) & (vol_trend == 1)  # Price down, Volume up
        bearish_divergence = (price_trend == 1) & (vol_trend == 0)  # Price up, Volume down
        
        # Price/Volume Momentum
        price_momentum = close.diff(period)
        vol_momentum = volume.diff(period)
        
        # Normalized Divergence Strength
        price_change_pct = close.pct_change(period)
        vol_change_pct = volume.pct_change(period)
        
        divergence_strength = abs(price_change_pct - vol_change_pct)
        
        # Confirmation
        confirmed_bullish = bullish_divergence & (close > close.shift(1))
        confirmed_bearish = bearish_divergence & (close < close.shift(1))
        
        return pd.DataFrame({
            'price_trend': price_trend,
            'vol_trend': vol_trend,
            'bullish_divergence': bullish_divergence.astype(int),
            'bearish_divergence': bearish_divergence.astype(int),
            'divergence_strength': divergence_strength,
            'confirmed_bullish': confirmed_bullish.astype(int),
            'confirmed_bearish': confirmed_bearish.astype(int)
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        vd_data = self.calculate(data, params)
        entries = (vd_data['confirmed_bullish'] == 1)
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': vd_data['divergence_strength'].clip(0, 1)}
    
    def generate_signals_dynamic(self, data, params):
        vd_data = self.calculate(data, params)
        entries = (vd_data['confirmed_bullish'] == 1)
        exits = (vd_data['confirmed_bearish'] == 1)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_divergence', index=data.index),
                'signal_strength': vd_data['divergence_strength'].clip(0, 1)}
    
    def get_ml_features(self, data, params):
        vd_data = self.calculate(data, params)
        return pd.DataFrame({
            'price_trend': vd_data['price_trend'],
            'vol_trend': vd_data['vol_trend'],
            'bullish_divergence': vd_data['bullish_divergence'],
            'bearish_divergence': vd_data['bearish_divergence'],
            'divergence_strength': vd_data['divergence_strength']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
