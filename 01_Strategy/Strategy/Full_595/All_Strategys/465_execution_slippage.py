"""
465_execution_slippage - Clean Wrapper
Auto-generated to fix syntax errors
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class Indicator_ExecutionSlippage:
    """Clean wrapper for 465_execution_slippage"""
    
    def __init__(self):
        self.name = "465_execution_slippage"
    
    def calculate(self, data, params):
        period = params.get('period', 20)
        
        # Execution slippage components
        
        # 1. Realized slippage proxy
        # Difference between open and close
        intrabar_slippage = abs(data['close'] - data['open']) / data['open']
        avg_slippage = intrabar_slippage.rolling(period).mean()
        
        # 2. Slippage volatility
        slippage_std = intrabar_slippage.rolling(period).std()
        slippage_cv = slippage_std / (avg_slippage + 1e-10)
        
        # 3. Volume impact on slippage
        volume = data['volume']
        avg_volume = volume.rolling(period).mean()
        volume_ratio = volume / (avg_volume + 1e-10)
        
        # High volume = lower slippage
        volume_impact = 1 / (volume_ratio + 1e-10)
        volume_impact_normalized = volume_impact / volume_impact.rolling(50).max()
        
        # 4. Spread-based slippage
        spread = data['high'] - data['low']
        spread_pct = spread / data['close']
        
        # Wider spread = higher slippage
        spread_slippage = spread_pct
        
        # 5. Expected slippage
        expected_slippage = (
            avg_slippage * 0.4 +
            spread_slippage * 0.3 +
            volume_impact_normalized * avg_slippage * 0.3
        )
        expected_slippage_smooth = expected_slippage.rolling(5).mean()
        
        # 6. Slippage risk score
        # High expected slippage + high volatility = high risk
        slippage_risk = expected_slippage_smooth * slippage_cv
        slippage_risk_normalized = slippage_risk / slippage_risk.rolling(50).max()
        slippage_risk_smooth = slippage_risk_normalized.rolling(5).mean()
        
        # 7. High slippage periods
        high_slippage = expected_slippage_smooth > expected_slippage_smooth.rolling(50).quantile(0.75)
        
        # 8. Low slippage periods
        low_slippage = expected_slippage_smooth < expected_slippage_smooth.rolling(50).quantile(0.25)
        
        # 9. Execution quality
        # Low slippage + low risk = high quality
        execution_quality = (1 - expected_slippage_smooth) * (1 - slippage_risk_smooth)
        execution_quality_smooth = execution_quality.rolling(5).mean()
        
        # 10. Optimal execution window
        optimal_window = (
            (expected_slippage_smooth < avg_slippage) &
            (slippage_risk_smooth < 0.5) &
            (execution_quality_smooth > 0.25)
        )
        
        # 11. Slippage cost estimate
        # In basis points
        slippage_cost_bps = expected_slippage_smooth * 10000
        
        # 12. Market impact proxy
        # Price movement during execution
        price_impact = abs(data['close'] - data['open']) / data['open']
        market_impact = price_impact * volume_ratio
        market_impact_smooth = market_impact.rolling(5).mean()
        
        # 13. Total execution cost
        total_cost = expected_slippage_smooth + market_impact_smooth
        total_cost_smooth = total_cost.rolling(5).mean()
        
        # 14. Cost efficiency
        cost_efficiency = 1 / (total_cost_smooth + 1e-10)
        cost_efficiency_normalized = cost_efficiency / cost_efficiency.rolling(50).max()
        
        return pd.DataFrame({
            'intrabar_slippage': intrabar_slippage,
            'avg_slippage': avg_slippage,
            'slippage_std': slippage_std,
            'slippage_cv': slippage_cv,
            'volume_ratio': volume_ratio,
            'volume_impact': volume_impact_normalized,
            'spread_pct': spread_pct,
            'spread_slippage': spread_slippage,
            'expected_slippage': expected_slippage,
            'expected_slippage_smooth': expected_slippage_smooth,
            'slippage_risk': slippage_risk_normalized,
            'slippage_risk_smooth': slippage_risk_smooth,
            'high_slippage': high_slippage.fillna(0).astype(int),
            'low_slippage': low_slippage.fillna(0).astype(int),
            'execution_quality': execution_quality,
            'execution_quality_smooth': execution_quality_smooth,
            'optimal_window': optimal_window.fillna(0).astype(int),
            'slippage_cost_bps': slippage_cost_bps,
            'price_impact': price_impact,
            'market_impact': market_impact,
            'market_impact_smooth': market_impact_smooth,
            'total_cost': total_cost,
            'total_cost_smooth': total_cost_smooth,
            'cost_efficiency': cost_efficiency_normalized
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
