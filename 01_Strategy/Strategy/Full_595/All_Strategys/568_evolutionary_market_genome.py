"""
568 - Evolutionary Market Genome
Ultimate Master Indicator: Genetic algorithm-inspired market evolution tracking
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class EvolutionaryMarketGenome:
    """
    Evolutionary Market Genome - Genetic evolution of market patterns
    
    Features:
    - Genetic fitness scoring
    - Pattern mutation detection
    - Natural selection simulation
    - Evolutionary pressure measurement
    - Adaptation rate tracking
    """
    
    def __init__(self):
        self.name = "Evolutionary Market Genome"
        self.version = "1.0"
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Calculate evolutionary genome score"""
        
        # Parameters
        evolution_period = params.get('evolution_period', 60)
        generation_period = params.get('generation_period', 20)
        fitness_period = params.get('fitness_period', 40)
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 1. Genetic Fitness Scoring
        returns = close.pct_change()
        
        # Survival fitness (positive returns)
        survival_rate = (returns > 0).rolling(fitness_period).mean()
        
        # Reproduction fitness (strong moves)
        strong_moves = (abs(returns) > returns.rolling(fitness_period).std()).astype(int)
        reproduction_rate = strong_moves.rolling(fitness_period).mean()
        
        # Resource fitness (volume support)
        volume_fitness = volume / volume.rolling(fitness_period).mean()
        volume_fitness = np.tanh(volume_fitness - 1)
        
        # Combined fitness
        genetic_fitness = (
            0.4 * survival_rate +
            0.3 * reproduction_rate +
            0.3 * volume_fitness
        )
        
        # 2. Pattern Mutation Detection
        # Pattern signature (rolling correlation with past)
        pattern_current = returns.rolling(generation_period).apply(
            lambda x: np.corrcoef(x, np.arange(len(x)))[0, 1] if len(x) > 1 else 0
        )
        pattern_previous = pattern_current.shift(generation_period)
        
        # Mutation rate (pattern change)
        mutation_rate = abs(pattern_current - pattern_previous)
        
        # Mutation impact
        volatility_change = returns.rolling(generation_period).std().pct_change(generation_period)
        mutation_impact = abs(volatility_change)
        
        pattern_mutation = (mutation_rate + mutation_impact) / 2
        
        # 3. Natural Selection Simulation
        # Selection pressure (market efficiency)
        price_efficiency = abs(close - close.shift(1)) / ((high - low) + 1e-10)
        selection_pressure = price_efficiency.rolling(fitness_period).mean()
        
        # Competitive advantage (relative strength)
        roc = close.pct_change(generation_period)
        competitive_advantage = roc / (roc.rolling(evolution_period).std() + 1e-10)
        competitive_advantage = np.tanh(competitive_advantage)
        
        # Survival of fittest
        fitness_rank = genetic_fitness.rolling(evolution_period).apply(
            lambda x: (x[-1] > x.mean()).astype(float) if len(x) > 0 else 0.5
        )
        
        natural_selection = (
            0.4 * selection_pressure +
            0.3 * competitive_advantage +
            0.3 * fitness_rank
        )
        
        # 4. Evolutionary Pressure Measurement
        # Environmental stress (volatility)
        environmental_stress = returns.rolling(fitness_period).std()
        stress_normalized = environmental_stress / environmental_stress.rolling(evolution_period).mean()
        
        # Population density (trading activity)
        population_density = volume.rolling(generation_period).mean() / volume.rolling(evolution_period).mean()
        
        # Resource scarcity (liquidity)
        liquidity = volume * close
        resource_scarcity = 1 / (liquidity / liquidity.rolling(fitness_period).mean() + 1e-10)
        resource_scarcity = np.tanh(resource_scarcity - 1)
        
        evolutionary_pressure = (
            0.4 * np.tanh(stress_normalized - 1) +
            0.3 * np.tanh(population_density - 1) +
            0.3 * resource_scarcity
        )
        
        # 5. Adaptation Rate Tracking
        # Speed of pattern change
        pattern_velocity = pattern_mutation.rolling(generation_period).mean()
        
        # Fitness improvement rate
        fitness_change = genetic_fitness.diff(generation_period)
        fitness_acceleration = fitness_change.diff(generation_period)
        
        # Adaptive response
        pressure_response = evolutionary_pressure.rolling(generation_period).corr(genetic_fitness)
        
        adaptation_rate = (
            0.4 * pattern_velocity +
            0.3 * np.tanh(fitness_acceleration * 10) +
            0.3 * abs(pressure_response)
        )
        
        # 6. Evolutionary Genome Score
        genome_score = (
            0.30 * genetic_fitness +
            0.20 * (1 - pattern_mutation) +
            0.25 * natural_selection +
            0.15 * (1 - abs(evolutionary_pressure)) +
            0.10 * adaptation_rate
        )
        
        # 7. Evolutionary Stage
        evolution_stage = pd.Series(0, index=data.index)
        evolution_stage[(genome_score > 0.6) & (adaptation_rate > 0.5)] = 3  # Thriving
        evolution_stage[(genome_score > 0.4) & (genome_score <= 0.6)] = 2  # Adapting
        evolution_stage[(genome_score > 0.2) & (genome_score <= 0.4)] = 1  # Surviving
        evolution_stage[genome_score <= 0.2] = 0  # Struggling
        
        # 8. Genome Stability
        genome_volatility = genome_score.rolling(fitness_period).std()
        genome_stability = 1 / (1 + genome_volatility)
        
        result = pd.DataFrame(index=data.index)
        result['genome_score'] = genome_score
        result['genetic_fitness'] = genetic_fitness
        result['pattern_mutation'] = pattern_mutation
        result['natural_selection'] = natural_selection
        result['evolutionary_pressure'] = evolutionary_pressure
        result['adaptation_rate'] = adaptation_rate
        result['evolution_stage'] = evolution_stage
        result['genome_stability'] = genome_stability
        
        return result
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL with manual exit logic"""
        
        indicator = self.calculate(data, params)
        
        # Entry: High fitness with strong adaptation
        entries = (
            (indicator['genome_score'] > 0.5) &
            (indicator['genetic_fitness'] > 0.6) &
            (indicator['adaptation_rate'] > 0.4) &
            (indicator['evolution_stage'] >= 2)
        )
        
        # TP/SL Parameters
        tp_pips = params.get('tp_pips', 100)
        sl_pips = params.get('sl_pips', 40)
        pip_value = 0.0001
        
        # Manual TP/SL Exit Logic
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
        
        # Dummy levels
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        
        signal_strength = indicator['genome_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic exit based on fitness decline"""
        
        indicator = self.calculate(data, params)
        
        # Entry: High fitness
        entries = (
            (indicator['genome_score'] > 0.5) &
            (indicator['genetic_fitness'] > 0.6) &
            (indicator['adaptation_rate'] > 0.4) &
            (indicator['evolution_stage'] >= 2)
        )
        
        # Exit: Fitness decline or high pressure
        exits = (
            (indicator['genome_score'] < 0.3) |
            (indicator['genetic_fitness'] < 0.4) |
            (indicator['evolution_stage'] <= 0)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits & (indicator['genome_score'] < 0.3)] = 'genome_deterioration'
        exit_reason[exits & (indicator['genetic_fitness'] < 0.4)] = 'fitness_decline'
        exit_reason[exits & (indicator['evolution_stage'] <= 0)] = 'survival_threat'
        
        signal_strength = indicator['genome_score'].clip(0, 1)
        
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
        features['genome_score'] = indicator['genome_score']
        features['genetic_fitness'] = indicator['genetic_fitness']
        features['pattern_mutation'] = indicator['pattern_mutation']
        features['natural_selection'] = indicator['natural_selection']
        features['evolutionary_pressure'] = indicator['evolutionary_pressure']
        features['adaptation_rate'] = indicator['adaptation_rate']
        features['evolution_stage'] = indicator['evolution_stage']
        features['genome_stability'] = indicator['genome_stability']
        
        # Additional features
        features['genome_momentum'] = indicator['genome_score'].diff(5)
        features['fitness_trend'] = indicator['genetic_fitness'].rolling(10).mean()
        features['mutation_volatility'] = indicator['pattern_mutation'].rolling(15).std()
        features['pressure_trend'] = indicator['evolutionary_pressure'].rolling(20).mean()
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Parameter grid for optimization"""
        return {
            'evolution_period': [50, 60, 75, 100, 125],
            'generation_period': [15, 20, 25, 30, 40],
            'fitness_period': [30, 40, 50, 60, 75],
            'tp_pips': [60, 75, 100, 125, 150],
            'sl_pips': [25, 30, 40, 50, 60]
        }
