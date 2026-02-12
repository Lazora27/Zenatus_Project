"""387 - Graph Centrality Indicator"""
import numpy as np
import pandas as pd

from typing import Dict
import warnings
warnings.filterwarnings("ignore")
__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__status__ = "Production"

class Indicator_GraphCentrality:
    """Graph Centrality - Price importance in correlation graph"""
    PARAMETERS = {
        'period': {'default': 20, 'values': [5,7,8,11,13,14,17,19,20,21,23,29], 'optimize': True},
        'tp_pips': {'default': 50, 'values': [30,40,50,60,75,100,125,150,200], 'optimize': True},
        'sl_pips': {'default': 25, 'values': [10,15,20,25,30,40,50], 'optimize': True}
    }
    
    def __init__(self):
        self.name, self.category, self.version = "GraphCentrality", "Statistics", __version__
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Create multiple time series (price at different lags)
        price = data['close']
        
        # Lagged series
        lag1 = price.shift(1).fillna(method='bfill')
        lag2 = price.shift(2).fillna(method='bfill')
        lag3 = price.shift(3).fillna(method='bfill')
        lag5 = price.shift(5).fillna(method='bfill')
        
        # Graph centrality measures
        degree_centrality = pd.Series(0.0, index=data.index)
        betweenness = pd.Series(0.0, index=data.index)
        
        for i in range(period, len(data)):
            # Build correlation matrix
            series_dict = {
                'current': price.iloc[i-period:i],
                'lag1': lag1.iloc[i-period:i],
                'lag2': lag2.iloc[i-period:i],
                'lag3': lag3.iloc[i-period:i],
                'lag5': lag5.iloc[i-period:i]
            }
            
            df = pd.DataFrame(series_dict)
            corr_matrix = df.corr().values
            
            # Threshold for edge creation
            threshold = 0.5
            
            # Adjacency matrix
            adj_matrix = (np.abs(corr_matrix) > threshold).astype(int)
            np.fill_diagonal(adj_matrix, 0)
            
            # Degree centrality (number of connections)
            degrees = adj_matrix.sum(axis=1)
            
            # Current price is node 0
            degree_centrality.iloc[i] = degrees[0] / (len(degrees) - 1) if len(degrees) > 1 else 0
            
            # Betweenness centrality (simplified)
            # How many shortest paths go through this node
            n_nodes = len(adj_matrix)
            betweenness_score = 0
            
            for source in range(n_nodes):
                for target in range(n_nodes):
                    if source != target and source != 0 and target != 0:
                        # Check if path goes through node 0
                        if adj_matrix[source, 0] and adj_matrix[0, target]:
                            betweenness_score += 1
            
            betweenness.iloc[i] = betweenness_score / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0
        
        # Combined centrality
        combined_centrality = (degree_centrality + betweenness) / 2
        
        # Smooth
        centrality_smooth = combined_centrality.rolling(5).mean()
        
        return pd.DataFrame({
            'degree_centrality': degree_centrality,
            'betweenness': betweenness,
            'combined_centrality': combined_centrality,
            'centrality_smooth': centrality_smooth
        })
    
    def generate_signals_fixed(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High centrality (price is important node)
        entries = result['centrality_smooth'] > 0.5
        
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
            'signal_strength': result['centrality_smooth']
        }
    
    def generate_signals_dynamic(self, data, params):
        result = self.calculate(data, params)
        
        # Entry: High centrality
        entries = result['combined_centrality'] > 0.5
        
        # Exit: Low centrality
        exits = result['combined_centrality'] < 0.3
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('centrality_loss', index=data.index),
            'signal_strength': result['centrality_smooth']
        }
    
    def get_ml_features(self, data, params):
        result = self.calculate(data, params)
        features = pd.DataFrame(index=data.index)
        
        features['graph_degree'] = result['degree_centrality']
        features['graph_betweenness'] = result['betweenness']
        features['graph_centrality'] = result['combined_centrality']
        features['graph_centrality_smooth'] = result['centrality_smooth']
        features['graph_high_centrality'] = (result['combined_centrality'] > 0.5).astype(int)
        
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

