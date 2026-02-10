"""390 - PageRank Signal"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_PageRankSignal:
    """PageRank Signal - Importance ranking in price network"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'damping': {'default': 0.85, 'values': [0.7,0.85,0.9], 'optimize': False},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "PageRankSignal", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        damping = params.get('damping', 0.85)
        
        # Build correlation network
        returns = data['close'].pct_change().fillna(0)
        
        pagerank_score = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Create lagged correlation network
            lags = [0, 1, 2, 3, 5]
            n_nodes = len(lags)
            
            # Build adjacency matrix based on correlations
            adj_matrix = np.zeros((n_nodes, n_nodes))
            
            for idx_a, lag_a in enumerate(lags):
                for idx_b, lag_b in enumerate(lags):
                    if idx_a != idx_b:
                        series_a = returns.iloc[i-period:i].shift(lag_a).fillna(0)
                        series_b = returns.iloc[i-period:i].shift(lag_b).fillna(0)
                        
                        corr = series_a.corr(series_b)
                        
                        if not np.isnan(corr) and abs(corr) > 0.3:
                            adj_matrix[idx_a, idx_b] = abs(corr)
            
            # Normalize adjacency (transition matrix)
            row_sums = adj_matrix.sum(axis=1)
            transition_matrix = np.zeros_like(adj_matrix)
            
            for idx in range(n_nodes):
                if row_sums[idx] > 0:
                    transition_matrix[idx] = adj_matrix[idx] / row_sums[idx]
            
            # PageRank algorithm
            pagerank = np.ones(n_nodes) / n_nodes
            
            for iteration in range(10):
                new_pagerank = (1 - damping) / n_nodes + damping * transition_matrix.T @ pagerank
                pagerank = new_pagerank
            
            # Current price importance (node 0)
            pagerank_score.iloc[i] = pagerank[0]
        
        # Normalize
        pagerank_normalized = pagerank_score / (pagerank_score.rolling(50).max() + 1e-10)
        
        # Smooth
        pagerank_smooth = pagerank_normalized.rolling(5).mean()
        
        return pd.DataFrame({
            'pagerank': pagerank_score,
            'pagerank_normalized': pagerank_normalized,
            'pagerank_smooth': pagerank_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High PageRank (important node)
        entries = result['pagerank_smooth'] > 0.6
        
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
            'signal_strength': result['pagerank_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High importance
        entries = result['pagerank_normalized'] > 0.6
        
        # Exit: Low importance
        exits = result['pagerank_normalized'] < 0.4
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('pagerank_drop', index=data.index),
            'signal_strength': result['pagerank_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['pagerank_score'] = result['pagerank']
        features['pagerank_normalized'] = result['pagerank_normalized']
        features['pagerank_smooth'] = result['pagerank_smooth']
        features['pagerank_high_importance'] = (result['pagerank_normalized'] > 0.6).astype(int)
        
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

