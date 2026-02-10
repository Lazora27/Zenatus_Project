"""
592 - Supreme Mastery Indicator
Ultimate Master Indicator: Represents supreme mastery over all market aspects
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class SupremeMasteryIndicator:
    """
    Supreme Mastery Indicator - Complete market mastery
    
    Features:
    - Mastery level measurement
    - Skill assessment
    - Expertise quantification
    - Proficiency scoring
    - Excellence detection
    """
    
    def __init__(self):
        self.name = "Supreme Mastery Indicator"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate supreme mastery score"""
        
        # Parameters
        mastery_period = params.get('mastery_period', 144)
        skill_period = params.get('skill_period', 89)
        expertise_period = params.get('expertise_period', 55)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        returns = close.pct_change()
        
        # 1. Mastery Level Measurement
        # Technical mastery
        trend_mastery = close.rolling(skill_period).apply(
            lambda x: abs(np.corrcoef(x, np.arange(len(x)))[0, 1]) if len(x) > 1 else 0
        )
        
        # Timing mastery
        at_optimal_entry = (close == close.rolling(expertise_period).min()).astype(float)
        timing_mastery = at_optimal_entry.rolling(skill_period).mean()
        
        # Risk mastery
        risk_reward = (high.rolling(expertise_period).max() - close) / (
            close - low.rolling(expertise_period).min() + 1e-10
        )
        risk_mastery = np.tanh(risk_reward - 2)
        
        mastery_level = (
            0.4 * trend_mastery +
            0.35 * timing_mastery +
            0.25 * risk_mastery
        )
        
        # 2. Skill Assessment
        # Execution skill
        execution_efficiency = abs(close - close.shift(1)) / ((high - low) + 1e-10)
        execution_skill = execution_efficiency.rolling(expertise_period).mean()
        
        # Prediction skill
        future_returns = returns.shift(-expertise_period)
        prediction_correct = (np.sign(returns.rolling(expertise_period).mean().shift(expertise_period)) == 
                            np.sign(future_returns))
        prediction_skill = prediction_correct.rolling(skill_period).mean()
        
        # Adaptation skill
        volatility = returns.rolling(expertise_period).std()
        volatility_change = volatility.pct_change(expertise_period)
        adaptation_response = -returns.rolling(expertise_period).std().pct_change(expertise_period)
        adaptation_skill = adaptation_response.rolling(skill_period).corr(volatility_change)
        
        skill_assessment = (
            0.4 * execution_skill +
            0.35 * prediction_skill +
            0.25 * abs(adaptation_skill)
        )
        
        # 3. Expertise Quantification
        # Years of experience (simulated by consistency)
        consistency = 1 / (1 + returns.rolling(mastery_period).std())
        
        # Success rate
        positive_returns = (returns > 0).rolling(skill_period).mean()
        
        # Profit factor
        gross_profit = returns.where(returns > 0, 0).rolling(skill_period).sum()
        gross_loss = abs(returns.where(returns < 0, 0).rolling(skill_period).sum())
        profit_factor = gross_profit / (gross_loss + 1e-10)
        profit_factor_normalized = np.tanh(profit_factor - 1.5)
        
        expertise_quantification = (
            0.4 * consistency +
            0.3 * positive_returns +
            0.3 * profit_factor_normalized
        )
        
        # 4. Proficiency Scoring
        # Overall proficiency
        technical_proficiency = trend_mastery
        fundamental_proficiency = consistency  # Use consistency instead of undefined truth_awareness
        psychological_proficiency = 1 / (1 + abs(returns).rolling(expertise_period).std())
        
        proficiency_score = (
            0.4 * technical_proficiency +
            0.3 * fundamental_proficiency +
            0.3 * psychological_proficiency
        )
        
        # 5. Excellence Detection
        # Detect moments of excellence
        performance_percentile = mastery_level.rolling(mastery_period).apply(
            lambda x: (x[-1] >= x).sum() / len(x) if len(x) > 0 else 0.5
        )
        excellence_moments = (performance_percentile > 0.9).astype(float)
        excellence_frequency = excellence_moments.rolling(skill_period).mean()
        
        # 6. Supreme Mastery
        supreme_mastery = (
            0.25 * mastery_level +
            0.25 * skill_assessment +
            0.20 * expertise_quantification +
            0.20 * proficiency_score +
            0.10 * excellence_frequency
        )
        
        # 7. Mastery Rank
        mastery_rank = pd.Series(0, index=data.index)
        mastery_rank[(supreme_mastery > 0.9) & (excellence_frequency > 0.5)] = 6  # Grand Master
        mastery_rank[(supreme_mastery > 0.8) & (supreme_mastery <= 0.9)] = 5  # Master
        mastery_rank[(supreme_mastery > 0.6) & (supreme_mastery <= 0.8)] = 4  # Expert
        mastery_rank[(supreme_mastery > 0.4) & (supreme_mastery <= 0.6)] = 3  # Advanced
        mastery_rank[(supreme_mastery > 0.2) & (supreme_mastery <= 0.4)] = 2  # Intermediate
        mastery_rank[(supreme_mastery > 0) & (supreme_mastery <= 0.2)] = 1  # Novice
        mastery_rank[supreme_mastery <= 0] = 0  # Beginner
        
        result = pd.DataFrame(index=data.index)
        result['supreme_mastery'] = supreme_mastery
        result['mastery_level'] = mastery_level
        result['skill_assessment'] = skill_assessment
        result['expertise_quantification'] = expertise_quantification
        result['proficiency_score'] = proficiency_score
        result['excellence_frequency'] = excellence_frequency
        result['mastery_rank'] = mastery_rank
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['supreme_mastery'] > 0.85) &
            (indicator['proficiency_score'] > 0.8) &
            (indicator['mastery_rank'] >= 5)
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
        signal_strength = indicator['supreme_mastery'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on mastery loss"""
        
        indicator = self.calculate(data, params)
        
        entries = (
            (indicator['supreme_mastery'] > 0.85) &
            (indicator['proficiency_score'] > 0.8) &
            (indicator['mastery_rank'] >= 5)
        )
        
        exits = (
            (indicator['supreme_mastery'] < 0.3) |
            (indicator['mastery_rank'] <= 2)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['supreme_mastery'] < 0.3)] = 'mastery_loss'
        exit_reason[exits & (indicator['mastery_rank'] <= 2)] = 'skill_degradation'
        
        signal_strength = indicator['supreme_mastery'].clip(0, 1)
        
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
        features['supreme_mastery'] = indicator['supreme_mastery']
        features['mastery_level'] = indicator['mastery_level']
        features['skill_assessment'] = indicator['skill_assessment']
        features['expertise_quantification'] = indicator['expertise_quantification']
        features['proficiency_score'] = indicator['proficiency_score']
        features['excellence_frequency'] = indicator['excellence_frequency']
        features['mastery_rank'] = indicator['mastery_rank']
        features['mastery_momentum'] = indicator['supreme_mastery'].diff(5)
        features['skill_trend'] = indicator['skill_assessment'].rolling(10).mean()
        features['proficiency_stability'] = indicator['proficiency_score'].rolling(15).std()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'mastery_period': [89, 100, 125, 144, 200],
            'skill_period': [55, 75, 89, 100, 125],
            'expertise_period': [34, 40, 55, 75, 100],
            'tp_pips': [250, 300, 400, 500, 600],
            'sl_pips': [100, 125, 150, 200, 250]
        }
