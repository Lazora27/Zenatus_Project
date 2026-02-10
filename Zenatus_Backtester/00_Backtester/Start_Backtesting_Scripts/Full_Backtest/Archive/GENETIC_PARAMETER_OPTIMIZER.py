# -*- coding: utf-8 -*-
"""
GENETIC PARAMETER OPTIMIZER - LAZORA VERFAHREN
===============================================
Optimiert Parameter individuell pro Indikator VOR dem Backtest
Verwendet genetische Algorithmen + Adaptive Sampling
Speichert optimierte Configs die vom Hauptbacktest geladen werden
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import importlib.util
import json
import warnings
from datetime import datetime
from typing import Dict, List, Tuple
warnings.filterwarnings('ignore')

try:
    import vectorbt as vbt
except:
    print("[FATAL] vectorbt not installed!")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Tier_4_Production"
DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data"
OUTPUT_PATH = BASE_PATH / "01_Backtest_System" / "Parameter_Configs"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

TIMEFRAME = '1h'
FREQ = '1H'
SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_JPY']  # Schneller Test mit 3 Symbolen
DATE_START = '2023-01-01'  # Kürzerer Zeitraum für Optimierung
DATE_END = '2025-09-20'

# GENETIC ALGORITHM SETTINGS
POPULATION_SIZE = 30  # Anzahl Individuen pro Generation (erhöht für bessere Exploration)
GENERATIONS = 15  # Anzahl Generationen (erhöht für bessere Konvergenz)
MUTATION_RATE = 0.20  # Erhöht für mehr Diversität
CROSSOVER_RATE = 0.75
ELITE_SIZE = 6  # Top 6 überleben immer

# TRADING CONFIG
INITIAL_CAPITAL = 10000
POSITION_SIZE = 100
pip_value = 0.0001

print("="*80)
print("GENETIC PARAMETER OPTIMIZER - LAZORA VERFAHREN")
print("="*80)
print(f"Indicators: {len(list(INDICATORS_PATH.glob('*.py')))}")
print(f"Symbols: {len(SYMBOLS)}")
print(f"Population: {POPULATION_SIZE}")
print(f"Generations: {GENERATIONS}")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================

DATA_CACHE = {}
print("\nLoading optimization data...")
for symbol in SYMBOLS:
    fp = DATA_PATH / TIMEFRAME / symbol / f"{symbol}_aggregated.csv"
    if not fp.exists():
        print(f"[WARN] {symbol} data not found")
        continue
    df = pd.read_csv(fp)
    df.columns = [c.lower() for c in df.columns]
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df = df[(df.index >= DATE_START) & (df.index < DATE_END)]
    DATA_CACHE[symbol] = df
    print(f"  {symbol}: {len(df)} bars")

# ============================================================================
# INDICATOR CATEGORY DETECTION
# ============================================================================

def detect_indicator_category(ind_name: str) -> str:
    """
    Erkennt Indikator-Kategorie basierend auf Namen
    Verschiedene Kategorien brauchen verschiedene Parameter-Ranges
    """
    name_lower = ind_name.lower()
    
    # TREND INDICATORS (lange Perioden)
    if any(x in name_lower for x in ['sma', 'ema', 'wma', 'dema', 'tema', 'trima', 
                                       'kama', 'hma', 'alma', 'jma', 't3', 'vidya',
                                       'frama', 'mcginley', 'vwma', 'linreg', 'lsma',
                                       'mama', 'smma', 'wilders', 'gaussian']):
        return 'trend'
    
    # MOMENTUM INDICATORS (kurze bis mittlere Perioden)
    if any(x in name_lower for x in ['rsi', 'stoch', 'williams', 'cci', 'roc', 
                                       'momentum', 'tsi', 'kdj', 'qqe', 'smi']):
        return 'momentum'
    
    # VOLATILITY INDICATORS (mittlere Perioden)
    if any(x in name_lower for x in ['bollinger', 'atr', 'keltner', 'donchian',
                                       'volatility', 'histvol']):
        return 'volatility'
    
    # VOLUME INDICATORS (mittlere bis lange Perioden)
    if any(x in name_lower for x in ['obv', 'mfi', 'cmf', 'vwap', 'force', 'ad',
                                       'volume', 'elderforce']):
        return 'volume'
    
    # OSCILLATOR (kurze bis mittlere Perioden)
    if any(x in name_lower for x in ['macd', 'ppo', 'apo', 'dpo', 'cmo', 'rvi',
                                       'awesome', 'accelerator', 'gator', 'trix']):
        return 'oscillator'
    
    # COMPLEX (spezielle Parameter)
    if any(x in name_lower for x in ['ichimoku', 'supertrend', 'psar', 'adx', 'dmi',
                                       'aroon', 'vortex', 'elder', 'alligator']):
        return 'complex'
    
    # DEFAULT: trend
    return 'trend'

# ============================================================================
# ADAPTIVE PARAMETER RANGES (LAZORA VERFAHREN)
# ============================================================================

def get_parameter_ranges(category: str) -> Dict:
    """
    Lazora-Verfahren: Adaptive Parameter-Ranges basierend auf Indikator-Kategorie
    Jede Kategorie hat optimale Perioden-Bereiche
    """
    ranges = {
        'trend': {
            'period_min': 10,
            'period_max': 200,
            'optimal_zones': [20, 50, 100, 150, 200],
            'period_count': 10,  # Mehr Perioden für Trend
            'tp_range': (30, 300),  # Größere Range für Trend
            'sl_range': (20, 150),
            'tp_sl_combos': 25,  # Mehr Kombinationen (>500 total möglich)
            'tp_zones': [50, 75, 100, 150, 200, 250],  # Hot Spots für TP
            'sl_zones': [30, 40, 50, 75, 100, 125]  # Hot Spots für SL
        },
        'momentum': {
            'period_min': 5,
            'period_max': 50,
            'optimal_zones': [7, 9, 14, 21, 28, 30],
            'period_count': 8,
            'tp_range': (15, 200),
            'sl_range': (10, 120),
            'tp_sl_combos': 20,
            'tp_zones': [25, 35, 50, 75, 100, 150],
            'sl_zones': [15, 20, 30, 40, 50, 75]
        },
        'volatility': {
            'period_min': 10,
            'period_max': 100,
            'optimal_zones': [14, 20, 25, 30, 40, 50],
            'period_count': 8,
            'tp_range': (25, 250),
            'sl_range': (15, 150),
            'tp_sl_combos': 22,
            'tp_zones': [40, 60, 80, 100, 150, 200],
            'sl_zones': [25, 35, 50, 75, 100, 125]
        },
        'volume': {
            'period_min': 10,
            'period_max': 100,
            'optimal_zones': [14, 20, 30, 40, 50],
            'period_count': 7,
            'tp_range': (30, 225),
            'sl_range': (20, 125),
            'tp_sl_combos': 18,
            'tp_zones': [45, 65, 90, 120, 175],
            'sl_zones': [30, 45, 60, 85, 110]
        },
        'oscillator': {
            'period_min': 5,
            'period_max': 50,
            'optimal_zones': [9, 12, 14, 21, 26, 30, 50],
            'period_count': 8,
            'tp_range': (20, 200),
            'sl_range': (12, 120),
            'tp_sl_combos': 20,
            'tp_zones': [30, 45, 65, 90, 125, 175],
            'sl_zones': [18, 28, 40, 55, 75, 100]
        },
        'complex': {
            'period_min': 9,
            'period_max': 100,
            'optimal_zones': [9, 14, 26, 52, 78],
            'period_count': 6,
            'tp_range': (30, 225),
            'sl_range': (20, 135),
            'tp_sl_combos': 16,
            'tp_zones': [50, 75, 110, 150, 200],
            'sl_zones': [35, 50, 70, 95, 120]
        }
    }
    
    return ranges.get(category, ranges['trend'])

# ============================================================================
# GENETIC ALGORITHM - INDIVIDUAL
# ============================================================================

class Individual:
    """Ein Individuum repräsentiert eine Parameter-Konfiguration"""
    
    def __init__(self, periods: List[int], tp_sl_combos: List[Tuple[int, int]]):
        self.periods = periods
        self.tp_sl_combos = tp_sl_combos
        self.fitness = 0.0
    
    def mutate(self, param_ranges: Dict):
        """Mutation: Zufällige Änderung der Parameter"""
        if np.random.random() < MUTATION_RATE:
            # Mutiere eine zufällige Period
            idx = np.random.randint(0, len(self.periods))
            new_period = np.random.randint(param_ranges['period_min'], 
                                          param_ranges['period_max'] + 1)
            self.periods[idx] = new_period
        
        if np.random.random() < MUTATION_RATE:
            # Mutiere ein zufälliges TP/SL Combo
            idx = np.random.randint(0, len(self.tp_sl_combos))
            tp = np.random.randint(param_ranges['tp_range'][0], 
                                  param_ranges['tp_range'][1])
            sl = np.random.randint(param_ranges['sl_range'][0], 
                                  param_ranges['sl_range'][1])
            if tp > sl:  # Nur valide Combos
                self.tp_sl_combos[idx] = (tp, sl)
    
    @staticmethod
    def crossover(parent1: 'Individual', parent2: 'Individual') -> 'Individual':
        """Crossover: Kombiniere zwei Eltern"""
        # Perioden: Mix von beiden Eltern
        crossover_point = len(parent1.periods) // 2
        child_periods = parent1.periods[:crossover_point] + parent2.periods[crossover_point:]
        
        # TP/SL: Mix von beiden Eltern
        crossover_point = len(parent1.tp_sl_combos) // 2
        child_combos = parent1.tp_sl_combos[:crossover_point] + parent2.tp_sl_combos[crossover_point:]
        
        return Individual(child_periods, child_combos)

# ============================================================================
# FITNESS EVALUATION
# ============================================================================

def evaluate_fitness(individual: Individual, ind_instance, symbol: str, df: pd.DataFrame) -> float:
    """
    Bewertet ein Individuum basierend auf Backtest-Performance
    Fitness = Gewichtete Kombination aus Sharpe, Profit Factor, Win Rate
    """
    try:
        total_score = 0.0
        valid_tests = 0
        
        # Teste mehrere Perioden mit mehreren TP/SL Combos
        test_periods = individual.periods[:min(4, len(individual.periods))]  # Top 4 Perioden
        test_combos = individual.tp_sl_combos[:min(3, len(individual.tp_sl_combos))]  # Top 3 Combos
        
        for period in test_periods:
            try:
                # Generate signals
                try:
                    signals = ind_instance.generate_signals_fixed(df, {'period': period})
                except TypeError:
                    try:
                        signals = ind_instance.generate_signals_fixed(df, {'period': period, 'vfactor': 0.7})
                    except:
                        signals = ind_instance.generate_signals_fixed(df, {})
                
                entries = signals['entries'].fillna(False).astype(bool)
                
                if entries.sum() < 3:
                    continue
                
                # Teste mit mehreren TP/SL Combos
                for tp, sl in test_combos:
                    try:
                        effective_tp = tp * pip_value
                        effective_sl = sl * pip_value
                        
                        pf = vbt.Portfolio.from_signals(
                            close=df['close'],
                            entries=entries,
                            exits=False,
                            tp_stop=effective_tp,
                            sl_stop=effective_sl,
                            init_cash=INITIAL_CAPITAL,
                            size=POSITION_SIZE,
                            size_type='amount',
                            fees=0.0,
                            freq=FREQ
                        )
                        
                        # Multi-Metric Fitness
                        sharpe = pf.sharpe_ratio()
                        profit_factor = pf.trades.profit_factor()
                        win_rate = pf.trades.win_rate()
                        
                        # Validierung
                        if np.isnan(sharpe) or np.isinf(sharpe):
                            sharpe = 0.0
                        if np.isnan(profit_factor) or np.isinf(profit_factor):
                            profit_factor = 1.0
                        if np.isnan(win_rate) or np.isinf(win_rate):
                            win_rate = 0.5
                        
                        # Gewichtete Score: 50% Sharpe, 30% Profit Factor, 20% Win Rate
                        score = (sharpe * 0.5) + ((profit_factor - 1.0) * 0.3) + (win_rate * 0.2)
                        total_score += score
                        valid_tests += 1
                    
                    except:
                        continue
            
            except:
                continue
        
        # Durchschnittliche Score
        if valid_tests > 0:
            return total_score / valid_tests
        return 0.0
    
    except:
        return 0.0

# ============================================================================
# GENETIC ALGORITHM - MAIN
# ============================================================================

def optimize_parameters(ind_file: Path) -> Dict:
    """
    Hauptfunktion: Optimiert Parameter für einen Indikator
    """
    ind_name = ind_file.stem
    try:
        ind_num = int(ind_name.split('_')[0])
    except:
        ind_num = 0
    
    print(f"\n{'='*80}")
    print(f"Optimizing: {ind_name}")
    print(f"{'='*80}")
    
    # Load indicator
    try:
        spec = importlib.util.spec_from_file_location(ind_name, ind_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        indicator_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and (attr_name.startswith('Indicator_') or attr_name.endswith('Indicator')):
                indicator_class = attr
                break
        
        if not indicator_class:
            print(f"[ERROR] No indicator class found in {ind_name}")
            return None
        
        ind_instance = indicator_class()
    
    except Exception as e:
        print(f"[ERROR] Failed to load: {str(e)[:100]}")
        return None
    
    # Detect category
    category = detect_indicator_category(ind_name)
    param_ranges = get_parameter_ranges(category)
    
    print(f"Category: {category}")
    print(f"Period Range: {param_ranges['period_min']}-{param_ranges['period_max']}")
    print(f"Optimal Zones: {param_ranges['optimal_zones']}")
    
    # Initialize population
    population = []
    for _ in range(POPULATION_SIZE):
        # Generate random periods (biased towards optimal zones)
        periods = []
        for _ in range(param_ranges['period_count']):
            if np.random.random() < 0.5 and param_ranges['optimal_zones']:
                # 50% chance: Pick from optimal zones
                period = np.random.choice(param_ranges['optimal_zones'])
            else:
                # 50% chance: Random from range
                period = np.random.randint(param_ranges['period_min'], 
                                          param_ranges['period_max'] + 1)
            periods.append(period)
        
        # Generate TP/SL combos (biased towards optimal zones)
        tp_sl_combos = []
        for _ in range(param_ranges['tp_sl_combos']):
            if np.random.random() < 0.6 and 'tp_zones' in param_ranges:
                # 60% chance: Pick from optimal zones
                tp = np.random.choice(param_ranges['tp_zones'])
                sl = np.random.choice(param_ranges['sl_zones'])
            else:
                # 40% chance: Random from range
                tp = np.random.randint(param_ranges['tp_range'][0], 
                                      param_ranges['tp_range'][1])
                sl = np.random.randint(param_ranges['sl_range'][0], 
                                      param_ranges['sl_range'][1])
            if tp > sl:  # Nur valide Kombinationen
                tp_sl_combos.append((tp, sl))
        
        if tp_sl_combos:
            population.append(Individual(periods, tp_sl_combos))
    
    # Genetic Algorithm
    best_individual = None
    best_fitness = -999
    
    for generation in range(GENERATIONS):
        # Evaluate fitness (nur auf einem Symbol für Geschwindigkeit)
        test_symbol = SYMBOLS[0]
        df = DATA_CACHE[test_symbol]
        
        for individual in population:
            individual.fitness = evaluate_fitness(individual, ind_instance, test_symbol, df)
        
        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Track best
        if population[0].fitness > best_fitness:
            best_fitness = population[0].fitness
            best_individual = population[0]
        
        print(f"Gen {generation+1}/{GENERATIONS}: Best Fitness = {best_fitness:.3f}")
        
        # Selection & Reproduction
        new_population = []
        
        # Elitism: Keep top performers
        new_population.extend(population[:ELITE_SIZE])
        
        # Crossover & Mutation
        while len(new_population) < POPULATION_SIZE:
            if np.random.random() < CROSSOVER_RATE:
                # Crossover
                parent1 = np.random.choice(population[:POPULATION_SIZE//2])
                parent2 = np.random.choice(population[:POPULATION_SIZE//2])
                child = Individual.crossover(parent1, parent2)
            else:
                # Clone
                parent = np.random.choice(population[:POPULATION_SIZE//2])
                child = Individual(parent.periods.copy(), parent.tp_sl_combos.copy())
            
            # Mutate
            child.mutate(param_ranges)
            new_population.append(child)
        
        population = new_population
    
    # Save best configuration
    if best_individual:
        config = {
            'indicator_num': ind_num,
            'indicator_name': ind_name,
            'category': category,
            'optimized_periods': sorted(list(set(best_individual.periods))),  # Unique & sorted
            'optimized_tp_sl_combos': best_individual.tp_sl_combos,
            'best_fitness': float(best_fitness),
            'optimization_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'param_ranges': param_ranges
        }
        
        output_file = OUTPUT_PATH / f"{ind_num:03d}_{ind_name}_config.json"
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ Optimized Config Saved!")
        print(f"Best Fitness: {best_fitness:.3f}")
        print(f"Periods: {config['optimized_periods']}")
        print(f"TP/SL Combos: {len(config['optimized_tp_sl_combos'])}")
        
        return config
    
    return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    all_indicators = sorted(INDICATORS_PATH.glob("*.py"))
    
    print(f"\nOptimizing {len(all_indicators)} indicators...")
    print("This will take some time...\n")
    
    successful = 0
    failed = 0
    
    for ind_file in all_indicators:
        try:
            config = optimize_parameters(ind_file)
            if config:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[ERROR] {ind_file.stem}: {str(e)[:100]}")
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"OPTIMIZATION COMPLETE!")
    print(f"{'='*80}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Configs saved in: {OUTPUT_PATH}")
    print(f"{'='*80}")
