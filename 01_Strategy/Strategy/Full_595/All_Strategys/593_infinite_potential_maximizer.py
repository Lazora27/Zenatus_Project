"""
593 - Infinite Potential Maximizer
Ultimate Master Indicator: Maximizes infinite market potential
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class InfinitePotentialMaximizer:
    """
    Infinite Potential Maximizer - Potential maximization
    
    Features:
    - Potential measurement
    - Opportunity detection
    - Capacity assessment
    - Possibility scoring
    - Maximum extraction
    """
    
    def __init__(self):
        self.name = "Infinite Potential Maximizer"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate infinite potential score"""
        
        # Parameters
        potential_period = params.get('potential_period', 100)
        opportunity_period = params.get('opportunity_period', 60)
        capacity_period = params.get('capacity_period', 40)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Potential Measurement
        # Upside potential
        upside_potential = (high.rolling(potential_period).max() - close) / close
        
        # Downside risk
        downside_risk = (close - low.rolling(potential_period).min()) / close
        
        # Net potential
        net_potential = upside_potential - downside_risk
        net_potential_normalized = np.tanh(net_potential * 2)
        
        # Momentum potential
        momentum = returns.rolling(capacity_period).mean()
        momentum_potential = momentum / (returns.rolling(capacity_period).std() + 1e-10)
        momentum_potential = np.tanh(momentum_potential)
        
        potential_score = (
            0.6 * net_potential_normalized +
            0.4 * momentum_potential
        )
        
        # 2. Opportunity Detection
        # High probability opportunities
        at_support = (close == close.rolling(opportunity_period).min()).astype(float)
        momentum_positive = (returns.rolling(capacity_period).mean() > 0).astype(float)
        volume_increasing = (volume > volume.rolling(opportunity_period).mean()).astype(float)
        
        opportunity_conditions = (at_support + momentum_positive + volume_increasing) / 3
        
        # Opportunity quality
        volatility = returns.rolling(capacity_period).std()
        low_volatility = (volatility < volatility.rolling(potential_period).median()).astype(float)
        
        opportunity_detection = (opportunity_conditions + low_volatility) / 2
        
        # 3. Capacity Assessment
        # Market capacity for movement
        atr = (high - low).rolling(capacity_period).mean()
        capacity_magnitude = atr / close
        
        # Volume capacity
        volume_capacity = volume / volume.rolling(potential_period).max()
        
        # Trend capacity
        trend_strength = close.rolling(opportunity_period).apply(
            lambda x: abs(np.polyfit(np.arange(len(x)), x, 1)[0]) if len(x) > 1 else 0
        )
        trend_capacity = trend_strength / (trend_strength.rolling(potential_period).max() + 1e-10)
        
        capacity_assessment = (
            0.4 * capacity_magnitude.clip(0, 1) +
            0.3 * volume_capacity +
            0.3 * trend_capacity
        )
        
        # 4. Possibility Scoring
        # What's possible given current conditions
        historical_max_gain = returns.rolling(capacity_period).max()
        current_momentum = returns.rolling(capacity_period).mean()
        
        possibility_ratio = current_momentum / (historical_max_gain + 1e-10)
        possibility_score = np.tanh(possibility_ratio * 10)
        
        # 5. Maximum Extraction
        # Extract maximum value
        efficiency = abs(close - close.shift(1)) / ((high - low) + 1e-10)
        extraction_efficiency = efficiency.rolling(capacity_period).mean()
        
        # Capture ratio
        upward_capture = returns.where(returns > 0, 0).rolling(opportunity_period).sum()
        total_upside = (high - low).rolling(opportunity_period).sum()
        capture_ratio = upward_capture / (total_upside + 1e-10)
        
        maximum_extraction = (extraction_efficiency + capture_ratio) / 2
        
        # 6. Infinite Potential
        infinite_potential = (
            0.30 * potential_score +
            0.25 * opportunity_detection +
            0.20 * capacity_assessment +
            0.15 * possibility_score +
            0.10 * maximum_extraction
        )
        
        # 7. Potential Level
        potential_level = pd.Series(0, index=data.index)
        potential_level[(infinite_potential > 0.85) & (opportunity_detection > 0.8)] = 5  # Infinite
        potential_level[(infinite_potential > 0.7) & (infinite_potential <= 0.85)] = 4  # Exceptional
        potential_level[(infinite_potential > 0.5) & (infinite_potential <= 0.7)] = 3  # High
        potential_level[(infinite_potential > 0.3) & (infinite_potential <= 0.5)] = 2  # Moderate
        potential_level[(infinite_potential > 0.1) & (infinite_potential <= 0.3)] = 1  # Low
        potential_level[infinite_potential <= 0.1] = 0  # Minimal
        
        result = pd.DataFrame(index=data.index)
        result['infinite_potential'] = infinite_potential
        result['potential_score'] = potential_score
        result['opportunity_detection'] = opportunity_detection
        result['capacity_assessment'] = capacity_assessment
        result['possibility_score'] = possibility_score
        result['maximum_extraction'] = maximum_extraction
        result['potential_level'] = potential_level
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['infinite_potential'] > 0.8) &
            (indicator['opportunity_detection'] > 0.75) &
            (indicator['potential_level'] >= 4)
        )
        
        tp_pips = params.get('tp_pips', 400)
        sl_pips = params.get('sl_pips', 150)
        pip_value = 0.0001
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price, tp_level, sl_level = 0, 0, 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip_value)
                sl_level = entry_price - (sl_pips * pip_value)
            elif in_position:
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        signal_strength = indicator['infinite_potential'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on potential exhaustion"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['infinite_potential'] > 0.8) &
            (indicator['opportunity_detection'] > 0.75) &
            (indicator['potential_level'] >= 4)
        )
        
        exits = (
            (indicator['infinite_potential'] < 0.2) |
            (indicator['potential_level'] <= 1)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['infinite_potential'] < 0.2)] = 'potential_exhausted'
        exit_reason[exits & (indicator['potential_level'] <= 1)] = 'opportunity_closed'
        
        signal_strength = indicator['infinite_potential'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extract ML features"""
        
        indicator = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        features['infinite_potential'] = indicator['infinite_potential']
        features['potential_score'] = indicator['potential_score']
        features['opportunity_detection'] = indicator['opportunity_detection']
        features['capacity_assessment'] = indicator['capacity_assessment']
        features['possibility_score'] = indicator['possibility_score']
        features['maximum_extraction'] = indicator['maximum_extraction']
        features['potential_level'] = indicator['potential_level']
        features['potential_momentum'] = indicator['infinite_potential'].diff(5)
        features['opportunity_trend'] = indicator['opportunity_detection'].rolling(10).mean()
        features['capacity_stability'] = indicator['capacity_assessment'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'potential_period': [75, 100, 125, 150, 200],
            'opportunity_period': [50, 60, 75, 100, 125],
            'capacity_period': [30, 40, 50, 60, 75],
            'tp_pips': [250, 300, 400, 500, 600],
            'sl_pips': [100, 125, 150, 200, 250]
        }
