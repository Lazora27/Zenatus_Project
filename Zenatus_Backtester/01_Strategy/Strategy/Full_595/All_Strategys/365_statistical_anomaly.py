"""365 - Statistical Anomaly Detector"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_StatisticalAnomaly:
    """Statistical Anomaly - Multi-method statistical anomaly detection"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'threshold': {'default': 2.0, 'values': [1.5,2.0,2.5,3.0], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "StatisticalAnomaly", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        threshold = params.get('threshold', 2.0)
        
        returns = data['close'].pct_change().fillna(0)
        
        # Method 1: Z-score
        mean = returns.rolling(period).mean()
        std = returns.rolling(period).std()
        zscore = (returns - mean) / (std + 1e-10)
        zscore_anomaly = (abs(zscore) > threshold).astype(int)
        
        # Method 2: IQR (Interquartile Range)
        q1 = returns.rolling(period).quantile(0.25)
        q3 = returns.rolling(period).quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        iqr_anomaly = ((returns < lower_bound) | (returns > upper_bound)).astype(int)
        
        # Method 3: Modified Z-score (using median)
        median = returns.rolling(period).median()
        mad = (returns - median).abs().rolling(period).median()
        modified_zscore = 0.6745 * (returns - median) / (mad + 1e-10)
        modified_anomaly = (abs(modified_zscore) > threshold).astype(int)
        
        # Method 4: Grubbs test-like (extreme values)
        max_val = returns.rolling(period).max()
        min_val = returns.rolling(period).min()
        grubbs_stat = np.maximum(
            abs(returns - mean) / (std + 1e-10),
            0
        )
        grubbs_anomaly = (grubbs_stat > threshold).astype(int)
        
        # Combine methods (consensus)
        anomaly_consensus = (zscore_anomaly + iqr_anomaly + modified_anomaly + grubbs_anomaly) / 4
        
        # Strong anomaly if multiple methods agree
        strong_anomaly = (anomaly_consensus > 0.5).astype(int)
        
        # Anomaly with positive momentum
        momentum = data['close'] > data['close'].shift(1)
        anomaly_signal = (strong_anomaly & momentum).astype(float)
        
        # Smooth
        anomaly_smooth = anomaly_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'zscore': zscore,
            'anomaly_consensus': anomaly_consensus,
            'strong_anomaly': strong_anomaly,
            'anomaly_signal': anomaly_signal,
            'anomaly_smooth': anomaly_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Strong anomaly
        entries = result['anomaly_smooth'] > 0.3
        
        # Manual TP/SL
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
        pip = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        
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
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': result['anomaly_consensus']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: Anomaly
        entries = result['strong_anomaly'] == 1
        
        # Exit: Normal
        exits = (result['strong_anomaly'] == 0) & (result['strong_anomaly'].shift(1) == 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('statistical_normal', index=data.index),
            'signal_strength': result['anomaly_consensus']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['stat_zscore'] = result['zscore']
        features['stat_consensus'] = result['anomaly_consensus']
        features['stat_strong_anomaly'] = result['strong_anomaly']
        features['stat_signal'] = result['anomaly_signal']
        features['stat_smooth'] = result['anomaly_smooth']
        features['stat_extreme_zscore'] = (abs(result['zscore']) > 2).astype(int)
        
        return features
    
    def validate_params(self, params):
        pass

    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100, 150],
            'sl_pips': [15, 25, 35, 50, 75]
        }

