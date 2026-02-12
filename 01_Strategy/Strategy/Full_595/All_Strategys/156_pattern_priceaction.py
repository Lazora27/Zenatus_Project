"""156 - Price Action Patterns"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PriceAction:
    """Price Action Patterns - Support/Resistance breaks, pin bars, inside bars"""
    PARAMETERS = {
        'lookback': {'default': 20, 'values': [10,14,20,30], 'optimize': True},
        'min_body_ratio': {'default': 0.3, 'values': [0.2,0.3,0.4], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PriceAction", "Pattern", __version__
    
    def calculate(self, data, params):
        lookback = params.get('lookback', 20)
        min_body_ratio = params.get('min_body_ratio', 0.3)
        
        # Candle components
        body = abs(data['close'] - data['open'])
        upper_shadow = data['high'] - data[['close', 'open']].max(axis=1)
        lower_shadow = data[['close', 'open']].min(axis=1) - data['low']
        candle_range = data['high'] - data['low']
        
        # Support and Resistance
        support = data['low'].rolling(lookback).min()
        resistance = data['high'].rolling(lookback).max()
        
        # Pattern detection
        patterns = pd.DataFrame(index=data.index)
        
        # 1. Pin Bar (rejection candle)
        patterns['pin_bar_bull'] = (
            (lower_shadow > candle_range * 0.6) &
            (body < candle_range * 0.3) &
            (data['close'] > data['open'])
        ).astype(int)
        
        patterns['pin_bar_bear'] = (
            (upper_shadow > candle_range * 0.6) &
            (body < candle_range * 0.3) &
            (data['close'] < data['open'])
        ).astype(int)
        
        # 2. Inside Bar
        patterns['inside_bar'] = (
            (data['high'] < data['high'].shift(1)) &
            (data['low'] > data['low'].shift(1))
        ).astype(int)
        
        # 3. Outside Bar
        patterns['outside_bar'] = (
            (data['high'] > data['high'].shift(1)) &
            (data['low'] < data['low'].shift(1))
        ).astype(int)
        
        # 4. Support Break
        patterns['support_break'] = (
            (data['close'] < support) &
            (data['close'].shift(1) >= support.shift(1))
        ).astype(int)
        
        # 5. Resistance Break
        patterns['resistance_break'] = (
            (data['close'] > resistance) &
            (data['close'].shift(1) <= resistance.shift(1))
        ).astype(int)
        
        # 6. Bullish Rejection at Support
        patterns['bull_rejection'] = (
            (abs(data['low'] - support) < candle_range * 0.1) &
            patterns['pin_bar_bull']
        ).astype(int)
        
        # 7. Bearish Rejection at Resistance
        patterns['bear_rejection'] = (
            (abs(data['high'] - resistance) < candle_range * 0.1) &
            patterns['pin_bar_bear']
        ).astype(int)
        
        # Composite signal
        bullish_score = (
            patterns['pin_bar_bull'] +
            patterns['resistance_break'] +
            patterns['bull_rejection']
        )
        
        bearish_score = (
            patterns['pin_bar_bear'] +
            patterns['support_break'] +
            patterns['bear_rejection']
        )
        
        signal = bullish_score - bearish_score
        
        return pd.DataFrame({
            'signal': signal,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'support': support,
            'resistance': resistance,
            **patterns
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        pa = self.calculate(data, params)
        # Entry on bullish price action
        entries = (pa['signal'] > 0)
        
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
                'signal_strength': abs(pa['signal']).clip(0, 3) / 3}
    
    def generate_signals_dynamic(self, data, params):
        pa = self.calculate(data, params)
        entries = (pa['signal'] > 0)
        exits = (pa['signal'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_pa', index=data.index),
                'signal_strength': abs(pa['signal']).clip(0, 3) / 3}
    
    def get_ml_features(self, data, params):
        pa = self.calculate(data, params)
        return pd.DataFrame({
            'pa_signal': pa['signal'],
            'pa_pin_bull': pa['pin_bar_bull'],
            'pa_pin_bear': pa['pin_bar_bear'],
            'pa_inside_bar': pa['inside_bar'],
            'pa_res_break': pa['resistance_break'],
            'pa_distance_support': (data['close'] - pa['support']) / data['close']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
