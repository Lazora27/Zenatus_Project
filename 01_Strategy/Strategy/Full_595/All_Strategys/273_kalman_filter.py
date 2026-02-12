"""273 - Kalman Filter"""
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_KalmanFilter:
    """Kalman Filter - Optimal State Estimation"""
    PARAMETERS = {
        'process_variance': {'default': 0.01, 'values': [0.001,0.01,0.1], 'optimize': True},
        'measurement_variance': {'default': 0.1, 'values': [0.01,0.1,1.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "KalmanFilter", "Statistics", __version__
    
    def calculate(self, data, params):
        process_var = params.get('process_variance', 0.01)
        measurement_var = params.get('measurement_variance', 0.1)
        close = data['close']
        
        # Simplified 1D Kalman Filter
        n = len(close)
        filtered = pd.Series(0.0, index=close.index)
        prediction_error = pd.Series(0.0, index=close.index)
        
        # Initialize
        x_est = close.iloc[0] if not pd.isna(close.iloc[0]) else 0
        p_est = 1.0
        
        for i in range(n):
            if pd.isna(close.iloc[i]):
                filtered.iloc[i] = x_est
                continue
            
            # Prediction
            x_pred = x_est
            p_pred = p_est + process_var
            
            # Update
            K = p_pred / (p_pred + measurement_var)  # Kalman gain
            x_est = x_pred + K * (close.iloc[i] - x_pred)
            p_est = (1 - K) * p_pred
            
            filtered.iloc[i] = x_est
            prediction_error.iloc[i] = close.iloc[i] - x_pred
        
        above_filtered = (close > filtered).astype(int)
        
        return pd.DataFrame({
            'filtered': filtered,
            'above_filtered': above_filtered,
            'prediction_error': prediction_error
        }, index=data.index).fillna(0)
    
    def generate_signals_fixed(self, data, params):
        kf_data = self.calculate(data, params)
        entries = (data['close'] > kf_data['filtered']) & (data['close'].shift(1) <= kf_data['filtered'].shift(1))
        tp, sl, pip = params.get('tp_pips', 50), params.get('sl_pips', 25), 0.0001
        exits, in_pos, ep, tp_l, sl_l = pd.Series(False, index=data.index), False, 0, 0, 0
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_pos:
                in_pos, ep = True, data['close'].iloc[i]
                tp_l, sl_l = ep + (tp * pip), ep - (sl * pip)
            elif in_pos and (data['high'].iloc[i] >= tp_l or data['low'].iloc[i] <= sl_l):
                exits.iloc[i], in_pos = True, False
        return {'entries': entries, 'exits': exits, 'tp_levels': pd.Series(np.nan, index=data.index),
                'sl_levels': pd.Series(np.nan, index=data.index), 'signal_strength': abs(kf_data['prediction_error'] / data['close']).clip(0, 0.1)*10}
    
    def generate_signals_dynamic(self, data, params):
        kf_data = self.calculate(data, params)
        entries = (data['close'] > kf_data['filtered']) & (data['close'].shift(1) <= kf_data['filtered'].shift(1))
        exits = (data['close'] < kf_data['filtered']) & (data['close'].shift(1) >= kf_data['filtered'].shift(1))
        return {'entries': entries, 'exits': exits, 'exit_reason': pd.Series('below_filtered', index=data.index),
                'signal_strength': abs(kf_data['prediction_error'] / data['close']).clip(0, 0.1)*10}
    
    def get_ml_features(self, data, params):
        return self.calculate(data, params)
    
    def validate_params(self, params): pass
    def get_parameter_grid(self): return {k: v.get('values', []) for k, v in self.PARAMETERS.items() if v.get('optimize')}
    def backtest_vectorbt(self, data, params, strategy_type='fixed', init_cash=10000, fees=0.0):
        s = self.generate_signals_fixed(data, params) if strategy_type == 'fixed' else self.generate_signals_dynamic(data, params)
        return vbt.Portfolio.from_signals(data['close'], entries=s['entries'], exits=s['exits'],
                                         tp_stop=s.get('tp_levels'), sl_stop=s.get('sl_levels'),
                                         freq='30T', init_cash=init_cash, fees=fees)
