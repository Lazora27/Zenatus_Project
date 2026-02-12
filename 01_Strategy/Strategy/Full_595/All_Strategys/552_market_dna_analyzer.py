"""
552_market_dna_analyzer.py
===========================
Indicator: Market DNA Analyzer
Category: Grand Finale / Pattern Genetics
Complexity: Elite

Description:
-----------
Analyzes the "genetic code" of market behavior by identifying fundamental
patterns that persist across timeframes. Extracts core market characteristics
and detects mutations in market DNA.

Key Features:
- DNA pattern extraction
- Genetic similarity analysis
- Mutation detection
- Core behavior identification

VectorBT-Compatible: Yes
ML-Ready: Yes (extracts 10+ features)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import talib


class Indicator_MarketDNAAnalyzer:
    """
    Market DNA Analyzer
    
    Analyzes fundamental market patterns (DNA).
    """
    
    def __init__(self):
        self.name = "Market DNA Analyzer"
        self.version = "1.0.0"
        self.category = "Grand Finale"
        
    @staticmethod
    def calculate(data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Calculate Market DNA metrics
        
        Parameters:
        - dna_period: Period for DNA analysis (default: 55)
        - gene_length: Length of genetic sequence (default: 8)
        - mutation_threshold: Threshold for mutation detection (default: 0.3)
        """
        dna_period = params.get('dna_period', 55)
        gene_length = params.get('gene_length', 8)
        mutation_threshold = params.get('mutation_threshold', 0.3)
        
        returns = data['close'].pct_change()
        
        # 1. DNA Sequence (pattern of up/down moves)
        # Encode as binary: 1=up, 0=down
        dna_sequence = (returns > 0).astype(int)
        
        # 2. Gene Patterns (recurring sequences)
        # Count frequency of specific patterns
        gene_frequency = dna_sequence.rolling(window=gene_length).sum() / gene_length
        
        # 3. DNA Stability (consistency of patterns)
        dna_stability = 1.0 - abs(gene_frequency - 0.5) * 2  # High when balanced
        
        # 4. Genetic Similarity (current vs historical DNA)
        genetic_similarity = pd.Series(0.0, index=data.index)
        
        for i in range(dna_period * 2, len(data)):
            current_dna = dna_sequence.iloc[i-gene_length:i].values
            historical_dna = dna_sequence.iloc[i-dna_period-gene_length:i-dna_period].values
            
            if len(current_dna) == gene_length and len(historical_dna) == gene_length:
                similarity = np.sum(current_dna == historical_dna) / gene_length
                genetic_similarity.iloc[i] = similarity
        
        # 5. DNA Mutation (sudden change in pattern)
        dna_mutation = (
            (genetic_similarity < mutation_threshold) &
            (genetic_similarity.shift(gene_length) > 0.7)
        ).astype(int)
        
        # 6. Core DNA (most persistent patterns)
        # Patterns that appear frequently
        core_pattern_strength = gene_frequency.rolling(window=dna_period).std()
        core_dna = (core_pattern_strength < 0.2).astype(int)
        
        # 7. DNA Regime (1=stable, 0=evolving, -1=mutating)
        dna_regime = pd.Series(0, index=data.index)
        dna_regime[core_dna == 1] = 1
        dna_regime[dna_mutation == 1] = -1
        
        # 8. Genetic Fitness (how well DNA performs)
        genetic_fitness = (dna_sequence.shift(1) == (returns > 0).astype(int)).astype(float)
        fitness_score = genetic_fitness.rolling(window=dna_period).mean()
        
        # 9. Optimal DNA Conditions (stable + high fitness)
        optimal_conditions = (
            (dna_regime == 1) &
            (fitness_score > 0.6) &
            (genetic_similarity > 0.7)
        ).astype(int)
        
        result = pd.DataFrame({
            'dna_sequence': dna_sequence,
            'gene_frequency': gene_frequency,
            'dna_stability': dna_stability,
            'genetic_similarity': genetic_similarity,
            'dna_mutation': dna_mutation,
            'core_dna': core_dna,
            'dna_regime': dna_regime,
            'fitness_score': fitness_score,
            'optimal_conditions': optimal_conditions
        }, index=data.index)
        
        return result.fillna(0)
    
    def generate_signals_fixed(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.a) Fixed TP/SL Strategy with MANUAL Exit Logic"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['fitness_score'] > 0.6) &
            (result['dna_regime'] == 1)
        )
        
        tp_pips = params.get('tp_pips', 50)
        sl_pips = params.get('sl_pips', 25)
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
        signal_strength = result['fitness_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(self, data: pd.DataFrame, params: Dict) -> Dict[str, pd.Series]:
        """A.b) Dynamic Exit Strategy - Indicator-based"""
        result = self.calculate(data, params)
        
        entries = (
            (result['optimal_conditions'] == 1) &
            (result['fitness_score'] > 0.6) &
            (result['dna_regime'] == 1)
        )
        
        exits = (
            (result['dna_mutation'] == 1) |
            (result['dna_regime'] == -1) |
            (result['fitness_score'] < 0.5)
        )
        
        exit_reason = pd.Series('', index=data.index)
        exit_reason[result['dna_mutation'] == 1] = 'dna_mutation'
        exit_reason[result['dna_regime'] == -1] = 'mutating_regime'
        
        signal_strength = result['fitness_score'].clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Extract ML features"""
        result = self.calculate(data, params)
        
        features = pd.DataFrame({
            'dna_sequence': result['dna_sequence'],
            'dna_gene_freq': result['gene_frequency'],
            'dna_stability': result['dna_stability'],
            'dna_similarity': result['genetic_similarity'],
            'dna_mutation': result['dna_mutation'],
            'dna_core': result['core_dna'],
            'dna_regime': result['dna_regime'],
            'dna_fitness': result['fitness_score'],
            'dna_optimal': result['optimal_conditions']
        }, index=data.index)
        
        return features.fillna(0)
    
    @staticmethod
    def get_parameter_grid() -> Dict:
        """Return parameter grid for optimization"""
        return {
            'dna_period': [34, 55, 89],
            'gene_length': [5, 8, 13],
            'mutation_threshold': [0.2, 0.3, 0.4],
            'tp_pips': [30, 50, 75, 100],
            'sl_pips': [15, 25, 40]
        }
