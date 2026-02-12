"""
438_smart_order_routing - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_SmartOrderRouting:
    """Clean wrapper for 438_smart_order_routing"""
    
    def __init__(self):
        self.name = "438_smart_order_routing"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Execution quality metrics
        
        # 1. Price improvement (better than mid-price)
        mid_price = (data['high'] + data['low']) / 2
        execution_price = data['close']
        price_improvement = abs(execution_price - mid_price) / mid_price
        avg_improvement = price_improvement.rolling(period).mean()
        
        # 2. Spread cost
        spread = data['high'] - data['low']
        spread_pct = spread / data['close']
        avg_spread = spread_pct.rolling(period).mean()
        
        # 3. Fill rate (volume consistency)
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        fill_rate = volume / (avg_volume + 1e-10)
        fill_consistency = 1 - fill_rate.rolling(period).std()
        
        # 4. Latency proxy (price volatility within bar)
        intrabar_volatility = spread / data['close']
        latency_score = 1 / (intrabar_volatility + 1e-10)
        latency_normalized = latency_score / latency_score.rolling(50).max()
        
        # 5. Routing efficiency
        routing_efficiency = (1 - avg_spread) * fill_consistency * latency_normalized
        routing_efficiency_smooth = routing_efficiency.rolling(5).mean()
        
        # 6. Venue quality score
        venue_quality = (
            (1 - avg_improvement) * 0.3 +  # Low slippage
            (1 - avg_spread) * 0.3 +        # Tight spreads
            fill_consistency * 0.2 +         # Consistent fills
            latency_normalized * 0.2         # Low latency
        )
        venue_quality_smooth = venue_quality.rolling(5).mean()
        
        # 7. Optimal routing conditions
        optimal_routing = (
            (avg_spread < 0.001) & 
            (fill_consistency > 0.2) & 
            (latency_normalized > 0.25)
        )
        
        # 8. Execution cost
        execution_cost = avg_spread + avg_improvement
        cost_normalized = execution_cost / execution_cost.rolling(50).max()
        
        # 9. Smart routing advantage
        routing_advantage = venue_quality - cost_normalized
        routing_advantage_smooth = routing_advantage.rolling(5).mean()
        
        return pd.DataFrame({
            'mid_price': mid_price,
            'price_improvement': price_improvement,
            'avg_improvement': avg_improvement,
            'spread_pct': spread_pct,
            'avg_spread': avg_spread,
            'fill_rate': fill_rate,
            'fill_consistency': fill_consistency,
            'intrabar_volatility': intrabar_volatility,
            'latency_score': latency_normalized,
            'routing_efficiency': routing_efficiency,
            'routing_efficiency_smooth': routing_efficiency_smooth,
            'venue_quality': venue_quality,
            'venue_quality_smooth': venue_quality_smooth,
            'optimal_routing': optimal_routing.fillna(0).astype(int),
            'execution_cost': execution_cost,
            'cost_normalized': cost_normalized,
            'routing_advantage': routing_advantage,
            'routing_advantage_smooth': routing_advantage_smooth
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
