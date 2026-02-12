"""026 - Average Directional Index (ADX)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_ADX:
    """Average Directional Index (ADX) - Trend Strength"""
    PARAMETERS = {
        'period': {'default': 14, 'min': 2, 'max': 50, 'values': [7,8,11,13,14,17,19,21,23,29], 'optimize': True, 'ml_feature': True},
        'threshold': {'default': 25, 'min': 10, 'max': 50, 'values': [15,20,25,30,35,40], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    def __init__(self):
        self.name, self.category, self.version = "ADX", "Trend", "1.0.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        period = params.get('period', 14)
        high, low, close = data['high'], data['low'], data['close']
        
        # True Range
        tr1, tr2, tr3 = high - low, abs(high - close.shift(1)), abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # Directional Movement
        up, down = high.diff(), -low.diff()
        pos_dm = ((up > down) & (up > 0)) * up
        neg_dm = ((down > up) & (down > 0)) * down
        
        # Smoothed DM
        pos_di = 100 * pos_dm.rolling(period).mean() / atr
        neg_di = 100 * neg_dm.rolling(period).mean() / atr
        
        # ADX
        dx = 100 * abs(pos_di - neg_di) / (pos_di + neg_di + 1e-10)
        adx = dx.rolling(period).mean()
        
        return pd.DataFrame({'adx': adx, 'pos_di': pos_di, 'neg_di': neg_di}, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict:
        result = self.calculate(data, params)
        threshold = params.get('threshold', 25)
        entries = (result['pos_di'] > result['neg_di']) & (result['pos_di'].shift(1) <= result['neg_di'].shift(1)) & (result['adx'] > threshold)
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        # TP/SL nur bei Entry setzen, NICHT forward-fillen!
                # Manuelle TP/SL Exit-Logik
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price, tp_level, sl_level = 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': result['adx'] / 100}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict:
        result = self.calculate(data, params)
        threshold = params.get('threshold', 25)
        entries = (result['pos_di'] > result['neg_di']) & (result['pos_di'].shift(1) <= result['neg_di'].shift(1)) & (result['adx'] > threshold)
        exits = (result['neg_di'] > result['pos_di']) & (result['neg_di'].shift(1) <= result['pos_di'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('adx_reverse', index=data.index), 'signal_strength': result['adx'] / 100}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['adx_value'], features['pos_di'], features['neg_di'] = result['adx'], result['pos_di'], result['neg_di']
        features['di_diff'] = result['pos_di'] - result['neg_di']
        features['adx_slope'] = result['adx'].diff()
        return features
    
    def validate_params(self, params: Dict): pass
    def get_parameter_grid(self) -> Dict: return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
