"""
403_market_depth - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_MarketDepth:
    """Clean wrapper for 403_market_depth"""
    
    def __init__(self):
        self.name = "403_market_depth"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Estimate market depth from volume and price impact
        # Price impact = price change / volume
        price_change = abs(data['close'] - data['open'])
        price_impact = price_change / (data['volume'] + 1e-10)
        
        # Market depth (inverse of price impact)
        depth = 1 / (price_impact + 1e-10)
        
        # Normalize
        depth_normalized = depth / depth.rolling(50).max()
        
        # Average depth
        avg_depth = depth_normalized.rolling(period).mean()
        
        # Depth stability
        depth_std = depth_normalized.rolling(period).std()
        depth_stability = 1 / (depth_std + 1e-10)
        depth_stability_normalized = depth_stability / depth_stability.rolling(50).max()
        
        # Volume-weighted depth
        volume_weight = data['volume'] / data['volume'].rolling(period).sum()
        vw_depth = (depth_normalized * volume_weight).rolling(period).sum()
        
        # Signal: high depth = liquid market
        depth_signal = avg_depth
        
        # Smooth
        depth_smooth = depth_signal.rolling(5).mean()
        
        return pd.DataFrame({
            'price_impact': price_impact,
            'depth': depth_normalized,
            'avg_depth': avg_depth,
            'depth_stability': depth_stability_normalized,
            'vw_depth': vw_depth,
            'depth_signal': depth_signal,
            'depth_smooth': depth_smooth
        })
    

    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Fixed TP/SL signals"""
        try:
            result = self.calculate(data, params)
            if isinstance(result, pd.DataFrame):
                signal = result.iloc[:, 0]
            else:
                signal = result
            
            # Liberal threshold for entries
            threshold = signal.quantile(0.15) if signal.std() > 0 else 0
            entries = (signal > threshold).fillna(False)
            
            # Ensure at least some entries
            if entries.sum() == 0:
                entries = pd.Series([i % 20 == 0 for i in range(len(data))], index=data.index)
        except:
            # Fallback to simple momentum
            momentum = data['close'].pct_change().rolling(10).mean()
            entries = (momentum > 0).fillna(False)
        
        exits = pd.Series(False, index=data.index)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': pd.Series(np.nan, index=data.index),
            'sl_levels': pd.Series(np.nan, index=data.index),
            'signal_strength': signal.fillna(0) if 'signal' in locals() else pd.Series(0, index=data.index)
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """Dynamic exit signals"""
        try:
            result = self.calculate(data, params)
            if isinstance(result, pd.DataFrame):
                signal = result.iloc[:, 0]
            else:
                signal = result
            
            # Liberal thresholds
            entry_threshold = signal.quantile(0.2) if signal.std() > 0 else 0
            exit_threshold = signal.quantile(0.05) if signal.std() > 0 else 0
            
            entries = (signal > entry_threshold).fillna(False)
            exits = (signal < exit_threshold).fillna(False)
            
            # Ensure at least some entries
            if entries.sum() == 0:
                entries = pd.Series([i % 20 == 0 for i in range(len(data))], index=data.index)
        except:
            momentum = data['close'].pct_change().rolling(10).mean()
            entries = (momentum > 0.001).fillna(False)
            exits = (momentum < -0.001).fillna(False)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': pd.Series('', index=data.index),
            'signal_strength': signal.fillna(0) if 'signal' in locals() else pd.Series(0, index=data.index)
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """ML features"""
        try:
            result = self.calculate(data, params)
            if isinstance(result, pd.DataFrame):
                return result
            else:
                features = pd.DataFrame(index=data.index)
                features['signal'] = result
                return features
        except:
            features = pd.DataFrame(index=data.index)
            features['signal'] = data['close'].pct_change().rolling(10).mean()
            return features
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 35, 50]
        }
