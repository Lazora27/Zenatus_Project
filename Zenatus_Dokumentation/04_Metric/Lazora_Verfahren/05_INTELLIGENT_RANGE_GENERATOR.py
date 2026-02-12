# -*- coding: utf-8 -*-
"""
INTELLIGENT PARAMETER RANGE GENERATOR - INDICATOR-SPECIFIC
===========================================================
Erstellt Indicator-spezifische Parameter-Ranges
Berücksichtigt: Indicator Type, Hot Spots, Fibonacci, Round Numbers
"""

import json
import numpy as np
from pathlib import Path

BASE_PATH = Path(r"D:\2_Trading\Superindikator_Alpha")
PARAM_PATH = BASE_PATH / "01_Backtest_System" / "Parameter_Optimization"
OUTPUT_PATH = BASE_PATH / "08_Lazora_Verfahren"

# ============================================================================
# INDICATOR-SPECIFIC INTELLIGENT RANGE GENERATOR
# ============================================================================

def generate_intelligent_range(ind_num, ind_name, param_name, default_value, param_type='int', param_min=None, param_max=None, num_steps=20):
    """
    INDICATOR-SPECIFIC Intelligente Range Generation
    
    Args:
        ind_num: Indicator Number
        ind_name: Indicator Name (für Type Detection)
        param_name: Parameter Name
        default_value: Default Value
        param_type: 'int', 'float', 'percent'
        param_min: Minimum allowed value
        param_max: Maximum allowed value
        num_steps: Number of values to generate
    
    Returns:
        dict with 'type', 'default', 'values', 'range_type'
    """
    
    param_lower = param_name.lower()
    ind_lower = ind_name.lower()
    
    # ========================================================================
    # PERIOD/LENGTH PARAMETERS
    # ========================================================================
    
    if any(kw in param_lower for kw in ['period', 'length', 'window', 'lookback', 'span']):
        
        # Base hot spots (universal)
        fibonacci = [2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
        round_numbers = [10, 20, 25, 30, 40, 50, 60, 75, 90, 100, 120, 150, 180, 200, 250, 300, 360, 365, 500]
        calendar = [20, 60, 120, 240, 252, 365]  # 252 = Trading Year!
        
        # INDICATOR-SPECIFIC RANGES
        if 'rsi' in ind_lower or 'momentum' in ind_lower or 'mfi' in ind_lower:
            # RSI/MFI/Momentum: 2-100 FULL RANGE (2-14 fast, 14-60 standard, 60-100 slow)
            hot_spots = [2, 3, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 20, 21, 25, 28, 30, 34, 40, 50, 55, 60, 70, 80, 90, 100]
            min_range = max(2, default_value // 3)
            max_range = min(100, default_value * 5)  # Extended to 100!
        
        elif 'ma' in ind_lower or 'average' in ind_lower or 'ema' in ind_lower or 'sma' in ind_lower or 'wma' in ind_lower or 'dema' in ind_lower or 'tema' in ind_lower:
            # Moving Averages: 3-500 FULL SPECTRUM (ALWAYS include institutional levels!)
            # Short: 3-20, Medium: 20-100, Long: 100-200, Institutional: 200-500
            hot_spots = [3, 5, 7, 8, 9, 10, 12, 13, 14, 15, 17, 20, 21, 25, 26, 30, 34, 40, 50, 55, 60, 75, 89, 90, 100, 120, 144, 150, 180, 200, 233, 240, 250, 252, 300, 365, 377, 500]
            
            # ALWAYS test up to 500 for MAs (institutional levels matter!)
            min_range = max(3, default_value // 3)
            max_range = 500  # ALWAYS 500!
        
        elif 'macd' in ind_lower or 'ppo' in ind_lower or 'apo' in ind_lower:
            # MACD: Specific for fast/slow/signal
            if 'fast' in param_lower or 'short' in param_lower:
                hot_spots = [5, 7, 8, 9, 10, 12, 13, 14, 15, 17, 20, 21]
            elif 'slow' in param_lower or 'long' in param_lower:
                hot_spots = [20, 21, 24, 26, 28, 30, 34, 40, 50, 55, 60]
            elif 'signal' in param_lower:
                hot_spots = [5, 7, 8, 9, 10, 12, 13, 15]
            else:
                hot_spots = [8, 9, 10, 12, 13, 14, 15, 20, 21, 26, 30, 34]
            min_range = max(5, default_value // 2)
            max_range = min(60, default_value * 2)
        
        elif 'stoch' in ind_lower:
            # Stochastic: 5-21
            hot_spots = [5, 7, 8, 9, 10, 12, 13, 14, 15, 20, 21]
            min_range = max(3, default_value // 2)
            max_range = min(34, default_value * 2)
        
        elif 'adx' in ind_lower or 'dmi' in ind_lower:
            # ADX/DMI: 7-28
            hot_spots = [7, 8, 10, 12, 13, 14, 15, 20, 21, 25, 28]
            min_range = max(5, default_value // 2)
            max_range = min(40, default_value * 2)
        
        elif 'bollinger' in ind_lower or 'keltner' in ind_lower or 'donchian' in ind_lower:
            # Bands: 10-50
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'atr' in ind_lower:
            # ATR: 7-50 (volatility measurement)
            hot_spots = [7, 8, 10, 12, 13, 14, 15, 20, 21, 25, 28, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'cci' in ind_lower:
            # CCI: 14-50 (Commodity Channel Index)
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'williams' in ind_lower or 'wpr' in ind_lower or '%r' in ind_lower:
            # Williams %R: 5-34
            hot_spots = [5, 7, 8, 10, 12, 13, 14, 15, 20, 21, 25, 28, 34]
            min_range = max(3, default_value // 2)
            max_range = min(55, default_value * 2)
        
        elif 'ichimoku' in ind_lower:
            # Ichimoku: Japanese time periods (9, 26, 52)
            if 'tenkan' in param_lower or 'conversion' in param_lower:
                hot_spots = [7, 8, 9, 10, 11, 12, 13]
            elif 'kijun' in param_lower or 'base' in param_lower:
                hot_spots = [20, 21, 24, 26, 28, 30, 34]
            elif 'senkou' in param_lower or 'span' in param_lower:
                hot_spots = [40, 44, 50, 52, 55, 60]
            else:
                hot_spots = [9, 26, 52]
            min_range = max(5, default_value // 2)
            max_range = min(120, default_value * 2)
        
        elif 'vortex' in ind_lower:
            # Vortex: 14-28
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 28]
            min_range = max(5, default_value // 2)
            max_range = min(55, default_value * 2)
        
        elif 'aroon' in ind_lower:
            # Aroon: 14-50
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'obv' in ind_lower or 'volume' in ind_lower:
            # Volume indicators: wider range
            hot_spots = [5, 10, 13, 14, 15, 20, 21, 25, 30, 34, 50, 60, 89, 100, 144, 200]
            min_range = max(3, default_value // 2)
            max_range = min(252, default_value * 4)
        
        elif 'pivot' in ind_lower or 'fibonacci' in ind_lower:
            # Pivot/Fib: Daily, Weekly, Monthly
            hot_spots = [1, 5, 20, 60, 120, 240, 252]  # 1=daily, 5=weekly, 20=monthly
            min_range = 1
            max_range = 252
        
        elif 'psar' in ind_lower or 'parabolic' in ind_lower:
            # Parabolic SAR: typically no period, but if present
            hot_spots = [5, 10, 14, 20, 30]
            min_range = max(2, default_value // 2)
            max_range = min(50, default_value * 2)
        
        elif 'trix' in ind_lower:
            # TRIX: 9-28
            hot_spots = [7, 8, 9, 10, 12, 13, 14, 15, 18, 20, 21, 25, 28]
            min_range = max(5, default_value // 2)
            max_range = min(50, default_value * 2)
        
        elif 'keltner' in ind_lower or 'donchian' in ind_lower:
            # Channel indicators: 10-50
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'rvi' in ind_lower or 'vigor' in ind_lower:
            # Relative Vigor Index: 10-20
            hot_spots = [8, 9, 10, 12, 13, 14, 15, 18, 20]
            min_range = max(5, default_value // 2)
            max_range = min(34, default_value * 2)
        
        elif 'cmo' in ind_lower or 'chande' in ind_lower:
            # Chande Momentum Oscillator: 9-28
            hot_spots = [7, 8, 9, 10, 12, 13, 14, 15, 20, 21, 25, 28]
            min_range = max(5, default_value // 2)
            max_range = min(50, default_value * 2)
        
        elif 'awesome' in ind_lower or 'accelerator' in ind_lower or 'gator' in ind_lower or 'alligator' in ind_lower:
            # Bill Williams indicators: 5, 8, 13, 34 (Fibonacci)
            hot_spots = [3, 5, 7, 8, 9, 10, 12, 13, 14, 15, 20, 21, 34]
            min_range = max(3, default_value // 2)
            max_range = min(55, default_value * 2)
        
        elif 'ultimate' in ind_lower:
            # Ultimate Oscillator: 7, 14, 28
            hot_spots = [5, 7, 8, 10, 12, 13, 14, 15, 20, 21, 25, 28, 30]
            min_range = max(3, default_value // 2)
            max_range = min(50, default_value * 2)
        
        elif 'dpo' in ind_lower or 'detrend' in ind_lower:
            # Detrended Price Oscillator: 14-28
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 28]
            min_range = max(5, default_value // 2)
            max_range = min(50, default_value * 2)
        
        elif 'mass' in ind_lower:
            # Mass Index: 9-25
            hot_spots = [7, 8, 9, 10, 12, 13, 14, 15, 20, 21, 25]
            min_range = max(5, default_value // 2)
            max_range = min(40, default_value * 2)
        
        elif 'qstick' in ind_lower:
            # Qstick: 8-20
            hot_spots = [7, 8, 9, 10, 12, 13, 14, 15, 18, 20]
            min_range = max(5, default_value // 2)
            max_range = min(34, default_value * 2)
        
        elif 'elder' in ind_lower:
            # Elder Ray: 13-34
            hot_spots = [8, 10, 12, 13, 14, 15, 20, 21, 25, 26, 30, 34]
            min_range = max(5, default_value // 2)
            max_range = min(55, default_value * 2)
        
        elif 'volatility' in ind_lower or 'stddev' in ind_lower:
            # Volatility indicators: 10-50
            hot_spots = [10, 12, 13, 14, 15, 20, 21, 25, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'entropy' in ind_lower or 'chaos' in ind_lower or 'fractal' in ind_lower:
            # Chaos/Entropy indicators: 10-50
            hot_spots = [8, 10, 12, 13, 14, 15, 20, 21, 25, 30, 34, 40, 50]
            min_range = max(5, default_value // 2)
            max_range = min(100, default_value * 3)
        
        elif 'hurst' in ind_lower:
            # Hurst Exponent: 10-100
            hot_spots = [10, 20, 25, 30, 40, 50, 60, 75, 90, 100]
            min_range = max(5, default_value // 2)
            max_range = min(200, default_value * 3)
        
        elif 'correlation' in ind_lower or 'cointegration' in ind_lower:
            # Correlation/Cointegration: 20-240
            hot_spots = [20, 30, 40, 50, 60, 90, 120, 180, 240, 252]
            min_range = max(10, default_value // 2)
            max_range = min(365, default_value * 3)
        
        else:
            # DEFAULT: FULL SPECTRUM (Fibonacci + Round + Calendar)
            hot_spots = sorted(set(fibonacci + round_numbers + calendar))
            min_range = max(2, default_value // 2)
            max_range = min(500, default_value * 3)
        
        # Apply constraints
        if param_min is not None:
            min_range = max(min_range, param_min)
        if param_max is not None:
            max_range = min(max_range, param_max)
        
        # Filter hot spots
        values = sorted(set([v for v in hot_spots if min_range <= v <= max_range]))
        
        # Fill to num_steps
        if len(values) < num_steps:
            additional = list(np.linspace(min_range, max_range, num_steps - len(values) + 10))
            additional = [int(round(v)) for v in additional]
            values = sorted(set(values + additional))
        
        # PRIORITY SAMPLING: Keep institutional levels (200, 252, 365, 500)!
        if len(values) > num_steps:
            # Identify key values (Fibonacci, Round, Calendar, Institutional)
            institutional = [v for v in values if v >= 200]  # 200, 252, 365, 500!
            fibonacci_vals = [v for v in values if v in fibonacci]
            round_vals = [v for v in values if v in round_numbers and v < 200]
            
            # Priority: institutional > fibonacci > round > others
            key_values = sorted(set(institutional + fibonacci_vals))
            remaining = num_steps - len(key_values)
            
            if remaining > 0:
                # Add round numbers
                round_vals = [v for v in round_vals if v not in key_values]
                if len(round_vals) > remaining:
                    step = max(1, len(round_vals) // remaining)
                    round_vals = [round_vals[i] for i in range(0, len(round_vals), step)][:remaining]
                key_values = sorted(set(key_values + round_vals))
                remaining = num_steps - len(key_values)
                
                if remaining > 0:
                    # Fill with others
                    other_values = [v for v in values if v not in key_values]
                    if len(other_values) > 0:
                        step = max(1, len(other_values) // remaining)
                        sampled_others = [other_values[i] for i in range(0, len(other_values), step)][:remaining]
                        values = sorted(set(key_values + sampled_others))
                    else:
                        values = key_values
                else:
                    values = key_values
            else:
                # Too many key values, keep all institutional + sample others
                values = sorted(set(institutional + fibonacci_vals[:num_steps - len(institutional)]))
        
        return {
            'type': 'int',
            'default': default_value,
            'values': values[:num_steps],
            'range_type': f'intelligent_period'
        }
    
    # ========================================================================
    # THRESHOLD/LEVEL PARAMETERS
    # ========================================================================
    
    if any(kw in param_lower for kw in ['threshold', 'level', 'overbought', 'oversold', 'upper', 'lower']):
        
        if param_type == 'percent' or (0 < default_value < 1):
            # Percentage (0-1)
            hot_spots = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 
                        0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
            
            min_range = max(0.05, default_value - 0.3)
            max_range = min(0.95, default_value + 0.3)
            
            if param_min is not None:
                min_range = max(min_range, param_min)
            if param_max is not None:
                max_range = min(max_range, param_max)
            
            values = [v for v in hot_spots if min_range <= v <= max_range]
            
            if len(values) < num_steps:
                additional = list(np.linspace(min_range, max_range, num_steps))
                values = sorted(set([round(v, 3) for v in values + additional]))
            
            return {
                'type': 'float',
                'default': default_value,
                'values': values[:num_steps],
                'range_type': 'intelligent_threshold_percent'
            }
        
        else:
            # Integer threshold (RSI/MFI/CCI/Williams/etc.)
            if 'rsi' in ind_lower or 'mfi' in ind_lower:
                # RSI/MFI: FULL RANGE 5-95!
                if 'oversold' in param_lower or default_value < 50:
                    # Oversold levels: 5-40
                    hot_spots = [5, 10, 15, 20, 25, 30, 35, 40]
                    min_range = 5
                    max_range = 45
                elif 'overbought' in param_lower or default_value > 50:
                    # Overbought levels: 60-95 (CRITICAL!)
                    hot_spots = [60, 65, 70, 75, 80, 85, 90, 95]
                    min_range = 55
                    max_range = 95
                else:
                    # General threshold: Full range
                    hot_spots = [5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 65, 70, 75, 80, 85, 90, 95]
                    min_range = 5
                    max_range = 95
            
            elif 'stoch' in ind_lower:
                # Stochastic: 0-100, focus on extremes
                if 'oversold' in param_lower or default_value < 50:
                    hot_spots = [5, 10, 15, 20, 25, 30]
                    min_range = 0
                    max_range = 40
                elif 'overbought' in param_lower or default_value > 50:
                    hot_spots = [70, 75, 80, 85, 90, 95]
                    min_range = 60
                    max_range = 100
                else:
                    hot_spots = [5, 10, 15, 20, 25, 30, 50, 70, 75, 80, 85, 90, 95]
                    min_range = 0
                    max_range = 100
            
            elif 'williams' in ind_lower or '%r' in ind_lower:
                # Williams %R: -100 to 0, typically -20 to -80
                if 'overbought' in param_lower or (default_value < 0 and default_value > -50):
                    hot_spots = [-5, -10, -15, -20, -25, -30]
                    min_range = -40
                    max_range = 0
                elif 'oversold' in param_lower or (default_value < -50):
                    hot_spots = [-70, -75, -80, -85, -90, -95]
                    min_range = -100
                    max_range = -60
                else:
                    hot_spots = [-5, -10, -15, -20, -25, -30, -50, -70, -75, -80, -85, -90, -95]
                    min_range = -100
                    max_range = 0
            
            elif 'cci' in ind_lower:
                # CCI: typically ±100, ±200
                if 'overbought' in param_lower or default_value > 0:
                    hot_spots = [50, 75, 100, 125, 150, 175, 200, 250, 300]
                    min_range = 50
                    max_range = 300
                elif 'oversold' in param_lower or default_value < 0:
                    hot_spots = [-50, -75, -100, -125, -150, -175, -200, -250, -300]
                    min_range = -300
                    max_range = -50
                else:
                    hot_spots = [-300, -250, -200, -175, -150, -125, -100, -75, -50, 0, 50, 75, 100, 125, 150, 175, 200, 250, 300]
                    min_range = -300
                    max_range = 300
            
            elif 'adx' in ind_lower:
                # ADX: 0-100, typically 20-40 for trend strength
                hot_spots = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80]
                min_range = 10
                max_range = 100
            
            else:
                # Generic thresholds
                hot_spots = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95]
                min_range = max(5, default_value - 30)
                max_range = min(95, default_value + 30)
            
            if param_min is not None:
                min_range = max(min_range, param_min)
            if param_max is not None:
                max_range = min(max_range, param_max)
            
            values = [v for v in hot_spots if min_range <= v <= max_range]
            
            if len(values) < num_steps:
                additional = list(np.linspace(min_range, max_range, num_steps))
                values = sorted(set([int(round(v)) for v in values + additional]))
            
            return {
                'type': 'int',
                'default': default_value,
                'values': values[:num_steps],
                'range_type': 'intelligent_threshold_int'
            }
    
    # ========================================================================
    # MULTIPLIER/FACTOR PARAMETERS
    # ========================================================================
    
    if any(kw in param_lower for kw in ['multiplier', 'factor', 'stddev', 'deviation', 'mult', 'sigma', 'alpha', 'beta']):
        
        # Base hot spots (Golden Ratio, Standard Deviations, Key Ratios)
        golden = 1.618
        hot_spots = [0.5, 0.75, 1.0, 1.25, 1.5, 1.618, 1.75, 2.0, 2.25, 2.5, 2.618, 2.75, 3.0, 3.5, 4.0, 5.0]
        
        # INDICATOR-SPECIFIC MULTIPLIERS
        if 'bollinger' in ind_lower or 'keltner' in ind_lower:
            # Bollinger/Keltner: 1.0-3.0 (typical 2.0)
            hot_spots = [1.0, 1.25, 1.5, 1.618, 1.75, 2.0, 2.25, 2.5, 2.618, 2.75, 3.0]
            min_range = max(0.5, default_value / 2)
            max_range = min(4.0, default_value * 2)
        
        elif 'atr' in ind_lower:
            # ATR multipliers: 1.0-5.0 (for stop-loss/take-profit)
            hot_spots = [1.0, 1.5, 1.618, 2.0, 2.5, 2.618, 3.0, 3.5, 4.0, 4.5, 5.0]
            min_range = max(0.5, default_value / 2)
            max_range = min(6.0, default_value * 2.5)
        
        elif 'acceleration' in param_lower or 'psar' in ind_lower:
            # Parabolic SAR acceleration: 0.01-0.2
            hot_spots = [0.01, 0.02, 0.03, 0.05, 0.1, 0.15, 0.2]
            min_range = 0.01
            max_range = 0.3
        
        elif 'alpha' in param_lower or 'smooth' in param_lower:
            # Smoothing factors: 0.1-0.9
            hot_spots = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
            min_range = 0.05
            max_range = 0.95
        
        elif 'fibonacci' in ind_lower:
            # Fibonacci multipliers: 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.618
            hot_spots = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.618]
            min_range = 0.236
            max_range = 2.618
        
        else:
            # Generic multipliers
            min_range = max(0.5, default_value / 2)
            max_range = min(5.0, default_value * 2.5)
        
        if param_min is not None:
            min_range = max(min_range, param_min)
        if param_max is not None:
            max_range = min(max_range, param_max)
        
        values = [v for v in hot_spots if min_range <= v <= max_range]
        
        if len(values) < num_steps:
            additional = list(np.linspace(min_range, max_range, num_steps))
            values = sorted(set([round(v, 3) for v in values + additional]))
        
        return {
            'type': 'float',
            'default': default_value,
            'values': values[:num_steps],
            'range_type': 'intelligent_multiplier'
        }
    
    # ========================================================================
    # FALLBACK: UNIVERSAL RANGE
    # ========================================================================
    
    min_range = default_value / 2 if default_value > 1 else 0.1
    max_range = default_value * 3 if default_value > 1 else 1.0
    
    if param_min is not None:
        min_range = max(min_range, param_min)
    if param_max is not None:
        max_range = min(max_range, param_max)
    
    if param_type == 'int':
        values = list(np.linspace(int(min_range), int(max_range), num_steps))
        values = sorted(set([int(round(v)) for v in values]))
    else:
        values = list(np.linspace(min_range, max_range, num_steps))
        values = [round(v, 4) for v in values]
    
    return {
        'type': param_type,
        'default': default_value,
        'values': values,
        'range_type': 'fallback_universal'
    }

# ============================================================================
# UPDATE HANDBOOK
# ============================================================================

def update_parameter_handbook():
    """Update handbook with intelligent ranges"""
    
    handbook_file = PARAM_PATH / "PARAMETER_HANDBOOK_COMPLETE.json"
    
    with open(handbook_file, 'r', encoding='utf-8') as f:
        handbook = json.load(f)
    
    print(f"Loaded {len(handbook)} indicators")
    
    updated_count = 0
    
    for ind in handbook:
        ind_num = ind['Indicator_Num']
        ind_name = ind['Indicator_Name']
        
        # Update Entry Params
        for param_name, param_config in ind['Entry_Params'].items():
            default = param_config.get('default', 14)
            param_type = param_config.get('type', 'int')
            param_min = param_config.get('min', None)
            param_max = param_config.get('max', None)
            
            # Generate intelligent range
            new_range = generate_intelligent_range(
                ind_num=ind_num,
                ind_name=ind_name,
                param_name=param_name,
                default_value=default,
                param_type=param_type,
                param_min=param_min,
                param_max=param_max,
                num_steps=20
            )
            
            # Update config
            param_config['values'] = new_range['values']
            param_config['range_type'] = new_range['range_type']
            param_config['start'] = min(new_range['values'])
            param_config['end'] = max(new_range['values'])
            param_config['num_steps'] = len(new_range['values'])
            
            updated_count += 1
        
        print(f"\r[{ind_num:03d}/{len(handbook)}] {ind_name[:40]:40s} | Updated {len(ind['Entry_Params'])} params", end='', flush=True)
    
    print(f"\n\nTotal parameters updated: {updated_count}")
    
    # Save updated handbook
    output_file = OUTPUT_PATH / "PARAMETER_HANDBOOK_INTELLIGENT.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(handbook, f, indent=2)
    
    print(f"Saved: {output_file}")
    
    return handbook

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("INTELLIGENT PARAMETER RANGE GENERATOR (INDICATOR-SPECIFIC)")
    print("="*80)
    
    handbook = update_parameter_handbook()
    
    print("\n" + "="*80)
    print("EXAMPLE RANGES (Indicator-Specific):")
    print("="*80)
    
    # Show examples
    examples = [
        ('001_trend_sma', 'SMA'),
        ('041_trend_rsi', 'RSI'),
        ('042_trend_macd', 'MACD'),
        ('043_trend_bollinger', 'Bollinger Bands'),
        ('044_trend_atr', 'ATR')
    ]
    
    for ind_prefix, desc in examples:
        ind = next((i for i in handbook if ind_prefix in i['Indicator_Name']), None)
        if ind:
            print(f"\n[{ind['Indicator_Num']:03d}] {desc} ({ind['Indicator_Name']})")
            for param_name, param_config in list(ind['Entry_Params'].items())[:2]:
                print(f"  {param_name}:")
                print(f"    Default: {param_config['default']}")
                print(f"    Range: {min(param_config['values'])} - {max(param_config['values'])}")
                print(f"    Values: {param_config['values'][:10]}... ({len(param_config['values'])} total)")
                print(f"    Type: {param_config['range_type']}")
    
    print("\n" + "="*80)
    print("DONE! Indicator-specific intelligent ranges generated.")
    print("="*80)
