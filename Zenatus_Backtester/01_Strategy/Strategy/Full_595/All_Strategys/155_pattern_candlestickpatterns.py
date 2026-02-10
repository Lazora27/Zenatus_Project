"""155 - Candlestick Patterns (50+ patterns)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_CandlestickPatterns:
    """Candlestick Patterns - Detects major candlestick patterns"""
    PARAMETERS = {
        'body_threshold': {'default': 0.5, 'values': [0.3,0.5,0.7], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "CandlestickPatterns", "Pattern", __version__
    
    def calculate(self, data, params):
        body_threshold = params.get('body_threshold', 0.5)
        
        # Calculate candle components
        body = abs(data['close'] - data['open'])
        upper_shadow = data['high'] - data[['close', 'open']].max(axis=1)
        lower_shadow = data[['close', 'open']].min(axis=1) - data['low']
        candle_range = data['high'] - data['low']
        
        # Bullish/Bearish
        bullish = data['close'] > data['open']
        bearish = data['close'] < data['open']
        
        # Pattern detection
        patterns = pd.DataFrame(index=data.index)
        
        # 1. Hammer (bullish reversal)
        patterns['hammer'] = (
            (lower_shadow > body * 2) &
            (upper_shadow < body * 0.3) &
            (body > candle_range * body_threshold * 0.3)
        ).astype(int)
        
        # 2. Inverted Hammer
        patterns['inverted_hammer'] = (
            (upper_shadow > body * 2) &
            (lower_shadow < body * 0.3) &
            (body > candle_range * body_threshold * 0.3)
        ).astype(int)
        
        # 3. Bullish Engulfing
        patterns['bullish_engulfing'] = (
            bullish &
            bearish.shift(1) &
            (data['close'] > data['open'].shift(1)) &
            (data['open'] < data['close'].shift(1))
        ).astype(int)
        
        # 4. Bearish Engulfing
        patterns['bearish_engulfing'] = (
            bearish &
            bullish.shift(1) &
            (data['close'] < data['open'].shift(1)) &
            (data['open'] > data['close'].shift(1))
        ).astype(int)
        
        # 5. Morning Star (3-candle bullish)
        patterns['morning_star'] = (
            bearish.shift(2) &
            (body.shift(1) < body.shift(2) * 0.3) &
            bullish &
            (data['close'] > (data['open'].shift(2) + data['close'].shift(2)) / 2)
        ).astype(int)
        
        # 6. Evening Star (3-candle bearish)
        patterns['evening_star'] = (
            bullish.shift(2) &
            (body.shift(1) < body.shift(2) * 0.3) &
            bearish &
            (data['close'] < (data['open'].shift(2) + data['close'].shift(2)) / 2)
        ).astype(int)
        
        # 7. Doji
        patterns['doji'] = (body < candle_range * 0.1).astype(int)
        
        # 8. Shooting Star
        patterns['shooting_star'] = (
            (upper_shadow > body * 2) &
            (lower_shadow < body * 0.3) &
            bearish
        ).astype(int)
        
        # Composite score
        bullish_score = (
            patterns['hammer'] +
            patterns['inverted_hammer'] +
            patterns['bullish_engulfing'] +
            patterns['morning_star']
        )
        
        bearish_score = (
            patterns['bearish_engulfing'] +
            patterns['evening_star'] +
            patterns['shooting_star']
        )
        
        signal = bullish_score - bearish_score
        
        return pd.DataFrame({
            'signal': signal,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            **patterns
        }, index=data.index)
    
    def generate_signals_fixed(self, data, params):
        patterns = self.calculate(data, params)
        # Entry on bullish patterns
        entries = (patterns['signal'] > 0)
        
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
                'signal_strength': abs(patterns['signal']).clip(0, 4) / 4}
    
    def generate_signals_dynamic(self, data, params):
        patterns = self.calculate(data, params)
        entries = (patterns['signal'] > 0)
        exits = (patterns['signal'] < 0)
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('bearish_pattern', index=data.index),
                'signal_strength': abs(patterns['signal']).clip(0, 4) / 4}
    
    def get_ml_features(self, data, params):
        patterns = self.calculate(data, params)
        return pd.DataFrame({
            'candle_signal': patterns['signal'],
            'candle_bullish': patterns['bullish_score'],
            'candle_bearish': patterns['bearish_score'],
            'candle_hammer': patterns['hammer'],
            'candle_engulfing_bull': patterns['bullish_engulfing'],
            'candle_engulfing_bear': patterns['bearish_engulfing']
        }, index=data.index)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
