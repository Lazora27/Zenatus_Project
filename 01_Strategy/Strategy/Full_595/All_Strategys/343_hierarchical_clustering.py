"""343 - Hierarchical Clustering Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_HierarchicalClustering:
    """Hierarchical Clustering - Multi-level market state clustering"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "HierarchicalClustering", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Features
        returns = data['close'].pct_change()
        
        # Level 1: Volatility-based clustering
        volatility = returns.rolling(period).std()
        vol_percentile = volatility.rolling(50).apply(
            lambda x: pd.Series(x).rank().iloc[-1] / len(x) if len(x) > 0 else 0.5
        ).fillna(0.5)
        
        level1_cluster = pd.Series(0, index=data.index)
        level1_cluster[vol_percentile > 0.5] = 1  # High vol cluster
        
        # Level 2: Trend-based clustering within vol clusters
        sma = data['close'].rolling(period).mean()
        trend = (data['close'] > sma).astype(int)
        
        level2_cluster = level1_cluster * 2 + trend
        
        # Level 3: Momentum-based clustering
        momentum = data['close'] - data['close'].shift(5)
        momentum_positive = (momentum > 0).astype(int)
        
        level3_cluster = level2_cluster * 2 + momentum_positive
        
        # Analyze cluster performance
        future_returns = returns.shift(-1)
        
        cluster_score = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            current_cluster = level3_cluster.iloc[i]
            
            # Historical performance of this cluster
            cluster_mask = (level3_cluster.iloc[i-period:i] == current_cluster)
            
            if cluster_mask.sum() > 0:
                cluster_returns = future_returns.iloc[i-period:i][cluster_mask]
                cluster_score.iloc[i] = (cluster_returns > 0).mean()
            else:
                cluster_score.iloc[i] = 0.5
        
        # Smooth
        cluster_smooth = cluster_score.rolling(5).mean()
        
        return pd.DataFrame({
            'level1_cluster': level1_cluster,
            'level2_cluster': level2_cluster,
            'level3_cluster': level3_cluster,
            'cluster_score': cluster_score,
            'cluster_smooth': cluster_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High cluster score
        entries = result['cluster_smooth'] > 0.6
        
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
            'signal_strength': result['cluster_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High score
        entries = result['cluster_smooth'] > 0.6
        
        # Exit: Cluster change
        exits = result['level3_cluster'].diff() != 0
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('hierarchy_change', index=data.index),
            'signal_strength': result['cluster_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['hc_level1'] = result['level1_cluster']
        features['hc_level2'] = result['level2_cluster']
        features['hc_level3'] = result['level3_cluster']
        features['hc_score'] = result['cluster_score']
        features['hc_smooth'] = result['cluster_smooth']
        features['hc_high_score'] = (result['cluster_smooth'] > 0.6).astype(int)
        
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

