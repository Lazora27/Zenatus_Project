"""021 - MESA Adaptive Moving Average (MAMA)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

class Indicator_MAMA:
    """MESA Adaptive Moving Average - Trend"""
    PARAMETERS = {
        'fastlimit': {'default': 0.5, 'min': 0.01, 'max': 1.0, 'values': [0.2,0.3,0.4,0.5,0.6,0.7,0.8], 'optimize': True, 'ml_feature': True},
        'slowlimit': {'default': 0.05, 'min': 0.001, 'max': 0.5, 'values': [0.02,0.03,0.04,0.05,0.06,0.08,0.1], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    def __init__(self):
        self.name, self.category, self.version = "MAMA", "Trend", "1.0.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        fastlimit, slowlimit = params.get('fastlimit', 0.5), params.get('slowlimit', 0.05)
        close = data['close']
        mama, fama = pd.Series(close.iloc[0], index=close.index), pd.Series(close.iloc[0], index=close.index)
        
        for i in range(1, len(close)):
            price = close.iloc[i]
            smooth = (4*price + 3*close.iloc[i-1] + 2*close.iloc[max(0,i-2)] + close.iloc[max(0,i-3)]) / 10
            std_val = close.rolling(20).std().iloc[i]
            if pd.isna(std_val) or std_val == 0:
                period = 20
            else:
                period = min(50, max(6, int(abs(price - close.iloc[i-1]) / std_val * 20)))
            alpha = fastlimit / period if period > 0 else slowlimit
            alpha = max(slowlimit, min(fastlimit, alpha))
            mama.iloc[i] = alpha * smooth + (1 - alpha) * mama.iloc[i-1]
            fama.iloc[i] = 0.5 * alpha * mama.iloc[i] + (1 - 0.5 * alpha) * fama.iloc[i-1]
        
        return pd.DataFrame({'mama': mama, 'fama': fama}, index=data.index)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict:
        result = self.calculate(data, params)
        entries = (result['mama'] > result['fama']) & (result['mama'].shift(1) <= result['fama'].shift(1))
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
        return {'entries': entries, 'exits': exits, 'tp_levels': tp_levels, 'sl_levels': sl_levels, 'signal_strength': abs(result['mama'] - result['fama']) / result['mama']}
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict:
        result = self.calculate(data, params)
        entries = (result['mama'] > result['fama']) & (result['mama'].shift(1) <= result['fama'].shift(1))
        exits = (result['mama'] < result['fama']) & (result['mama'].shift(1) >= result['fama'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('mama_cross', index=data.index), 'signal_strength': abs(result['mama'] - result['fama']) / result['mama']}
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        features['mama_value'], features['fama_value'] = result['mama'], result['fama']
        features['mama_fama_diff'] = result['mama'] - result['fama']
        return features
    
    def validate_params(self, params: Dict): pass
    def get_parameter_grid(self) -> Dict: return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0):
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
