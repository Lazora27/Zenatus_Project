"""061 - Trix (Triple Exponential Average)"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")

__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_Trix:
    """Trix - Triple EMA Rate of Change"""
    PARAMETERS = {
        'period': {'default': 15, 'min': 5, 'max': 50, 'values': [5,7,8,11,13,14,15,17,19,21,23,29,31,34,37,41,43,47], 'optimize': True, 'ml_feature': True},
        'signal_period': {'default': 9, 'min': 3, 'max': 20, 'values': [3,5,7,8,9,11,13,14,17,19], 'optimize': True, 'ml_feature': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    def __init__(self):
        self.name, self.category, self.version = "Trix", "Momentum", __version__
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Trix = ROC(EMA(EMA(EMA(close))))"""
        self.validate_params(params)
        period, signal_period = params.get('period', 15), params.get('signal_period', 9)
        ema1 = data['close'].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        trix = ((ema3 - ema3.shift(1)) / ema3.shift(1)) * 100
        signal = trix.ewm(span=signal_period, adjust=False).mean()
        return pd.DataFrame({'trix': trix.fillna(0), 'signal': signal.fillna(0)}, index=data.index)
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        result = self.calculate(data, params)
        trix, signal = result['trix'], result['signal']
        entries = (trix > signal) & (trix.shift(1) <= signal.shift(1))
        tp_pips, sl_pips, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_position, entry_price, tp_level, sl_level = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position, entry_price = True, data['close'].iloc[i]
                tp_level, sl_level = entry_price + (tp_pips * pip), entry_price - (sl_pips * pip)
            elif in_position and (data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level):
                exits.iloc[i], in_position = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index), 
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(trix - signal).clip(0, 1) / 1}
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        result = self.calculate(data, params)
        trix, signal = result['trix'], result['signal']
        entries, exits = (trix > signal) & (trix.shift(1) <= signal.shift(1)), (trix < signal) & (trix.shift(1) >= signal.shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('trix_signal_cross', index=data.index), 'signal_strength': abs(trix - signal).clip(0, 1) / 1}
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        result = self.calculate(data, params)
        return pd.DataFrame({'trix_value': result['trix'], 'trix_signal': result['signal'], 'trix_divergence': result['trix'] - result['signal'], 'trix_positive': (result['trix'] > 0).astype(int)}, index=data.index)
    def validate_params(self, params: Dict) -> None:
        for k, v in params.items():
            if k in self.PARAMETERS and ('min' in self.PARAMETERS[k] and v < self.PARAMETERS[k]['min'] or 'max' in self.PARAMETERS[k] and v > self.PARAMETERS[k]['max']):
                raise ValueError(f"{k} out of range")
    def get_parameter_grid(self) -> Dict:
        return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data: pd.DataFrame, params: Dict, strategy_type: str = 'fixed', init_cash: float = 10000, fees: float = 0.0) -> vbt.Portfolio:
        signals = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=signals['entries'], exits=signals['exits'], tp_stop=signals.get('tp_levels'), sl_stop=signals.get('sl_levels'), freq='30T', init_cash=init_cash, fees=fees)
