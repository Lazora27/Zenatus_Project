"""
001 - Simple Moving Average (SMA)
Einfachster Trend-Indikator, Basis für viele andere
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings("ignore")

__version__ = "1.0.0"
__author__ = "Nikola Cedomir Petar Cekic"
__date__ = "2025-10-02"
__status__ = "Production"


class Indicator_SMA:
    """
    Simple Moving Average (SMA) - Trend
    
    Beschreibung:
        Arithmetischer Durchschnitt der letzten N Perioden.
        Glättet Preisbewegungen und zeigt Trend-Richtung.
    
    Parameters:
        - period: Lookback-Periode (2-200)
        - tp_pips: Take Profit in Pips (20-200)
        - sl_pips: Stop Loss in Pips (10-100)
    
    Signals:
        - A.a: Fixed TP/SL - Entry bei Price Cross, Exit bei TP/SL
        - A.b: Dynamic Exit - Entry bei Price Cross, Exit bei Reverse Cross
    """
    
    # Parameter Definition (Fibonacci + Primzahlen)
    PARAMETERS = {
        'period': {
            'default': 20,
            'min': 2,
            'max': 200,
            'values': [2,3,5,7,8,11,13,17,19,21,23,29,31,34,37,41,43,47,53,55,59,61,67,71,73,79,83,89],
            'step': 1,
            'optimize': True,
            'ml_feature': True,
            'description': 'SMA lookback period'
        },
        'tp_pips': {
            'default': 50,
            'min': 20,
            'max': 200,
            'values': [30, 40, 50, 60, 75, 100, 125, 150, 200],
            'step': 10,
            'optimize': True,
            'ml_feature': False,
            'description': 'Take Profit in pips'
        },
        'sl_pips': {
            'default': 25,
            'min': 10,
            'max': 100,
            'values': [10, 15, 20, 25, 30, 40, 50],
            'step': 5,
            'optimize': True,
            'ml_feature': False,
            'description': 'Stop Loss in pips'
        }
    }
    
    def __init__(self):
        self.name = "SMA"
        self.category = "Trend"
        self.version = __version__
    
    def calculate(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """
        Berechnet Simple Moving Average.
        
        Formula: SMA = Sum(Close, N) / N
        
        Args:
            data: OHLCV DataFrame mit 'close' Spalte
            params: {'period': int}
            
        Returns:
            pd.Series: SMA Werte
        """
        self.validate_params(params)
        
        period = params.get('period', self.PARAMETERS['period']['default'])
        
        # Simple Moving Average
        sma = data['close'].rolling(window=period, min_periods=1).mean()
        
        return sma
    
    def generate_signals_fixed(
        self, 
        data: pd.DataFrame, 
        params: Dict
    ) -> Dict[str, pd.Series]:
        """
        A.a) Fixed TP/SL Strategie.
        
        Entry Long: Price crosses above SMA
        Entry Short: Price crosses below SMA
        Exit: Fixed TP/SL levels
        
        Args:
            data: OHLCV DataFrame
            params: Parameter Dictionary
            
        Returns:
            Dict mit entries, exits, tp_levels, sl_levels, signal_strength
        """
        # Berechne SMA
        sma = self.calculate(data, params)
        
        # Entry Signals
        # Long: Price crosses above SMA
        long_entries = (data['close'] > sma) & (data['close'].shift(1) <= sma.shift(1))
        
        # Short: Price crosses below SMA (für später, aktuell nur Long)
        # short_entries = (data['close'] < sma) & (data['close'].shift(1) >= sma.shift(1))
        
        entries = long_entries
        
        # Fixed TP/SL
        tp_pips = params.get('tp_pips', self.PARAMETERS['tp_pips']['default'])
        sl_pips = params.get('sl_pips', self.PARAMETERS['sl_pips']['default'])
        
        pip = 0.0001  # For Forex pairs
        
        # Manuelle TP/SL Exit-Logik (da VectorBT's tp_stop/sl_stop nicht richtig funktioniert)
        tp_level = data['close'].iloc[0] + (tp_pips * pip)
        sl_level = data['close'].iloc[0] - (sl_pips * pip)
        
        exits = pd.Series(False, index=data.index)
        in_position = False
        entry_price = 0
        
        for i in range(1, len(data)):
            if entries.iloc[i] and not in_position:
                in_position = True
                entry_price = data['close'].iloc[i]
                tp_level = entry_price + (tp_pips * pip)
                sl_level = entry_price - (sl_pips * pip)
            elif in_position:
                # Check TP/SL
                if data['high'].iloc[i] >= tp_level or data['low'].iloc[i] <= sl_level:
                    exits.iloc[i] = True
                    in_position = False
        
        # Dummy TP/SL levels für VectorBT (werden nicht verwendet)
        tp_levels = pd.Series(np.nan, index=data.index)
        sl_levels = pd.Series(np.nan, index=data.index)
        
        # Signal Strength: Distance from SMA
        signal_strength = abs(data['close'] - sma) / sma
        signal_strength = signal_strength.clip(0, 1)  # Normalize to 0-1
        
        return {
            'entries': entries,
            'exits': exits,
            'tp_levels': tp_levels,
            'sl_levels': sl_levels,
            'signal_strength': signal_strength
        }
    
    def generate_signals_dynamic(
        self, 
        data: pd.DataFrame, 
        params: Dict
    ) -> Dict[str, pd.Series]:
        """
        A.b) Dynamic Exit Strategie.
        
        Entry Long: Price crosses above SMA
        Exit: Price crosses below SMA (Reverse Cross)
        
        Args:
            data: OHLCV DataFrame
            params: Parameter Dictionary
            
        Returns:
            Dict mit entries, exits, exit_reason, signal_strength
        """
        # Berechne SMA
        sma = self.calculate(data, params)
        
        # Entry: Price crosses above SMA
        entries = (data['close'] > sma) & (data['close'].shift(1) <= sma.shift(1))
        
        # Dynamic Exit: Price crosses below SMA
        exits = (data['close'] < sma) & (data['close'].shift(1) >= sma.shift(1))
        
        # Exit Reason
        exit_reason = pd.Series('', index=data.index)
        exit_reason[exits] = 'sma_reverse_cross'
        
        # Signal Strength
        signal_strength = abs(data['close'] - sma) / sma
        signal_strength = signal_strength.clip(0, 1)
        
        return {
            'entries': entries,
            'exits': exits,
            'exit_reason': exit_reason,
            'signal_strength': signal_strength
        }
    
    def get_ml_features(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Extrahiert ML-Features aus SMA.
        
        Features:
            1. sma_value: Raw SMA value
            2. sma_normalized: Normalized (0-1)
            3. sma_slope: Rate of change
            4. sma_acceleration: 2nd derivative
            5. sma_percentile: Percentile rank
            6. distance_from_price: (Price - SMA) / Price
            7. distance_pct: Percentage distance
            8. above_sma: Boolean flag
            9. cross_up: Bullish cross
            10. cross_down: Bearish cross
        
        Args:
            data: OHLCV DataFrame
            params: Parameter Dictionary
            
        Returns:
            pd.DataFrame: ML Features
        """
        sma = self.calculate(data, params)
        
        features = pd.DataFrame(index=data.index)
        
        # 1. Raw value
        features['sma_value'] = sma
        
        # 2. Normalized (0-1) über Rolling Window
        rolling_min = sma.rolling(100, min_periods=1).min()
        rolling_max = sma.rolling(100, min_periods=1).max()
        features['sma_normalized'] = (sma - rolling_min) / (rolling_max - rolling_min + 1e-10)
        
        # 3. Slope (1st derivative)
        features['sma_slope'] = sma.diff()
        
        # 4. Acceleration (2nd derivative)
        features['sma_acceleration'] = sma.diff().diff()
        
        # 5. Percentile rank
        features['sma_percentile'] = sma.rolling(100, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else 0.5
        )
        
        # 6. Distance from price (absolute)
        features['distance_from_price'] = data['close'] - sma
        
        # 7. Distance percentage
        features['distance_pct'] = (data['close'] - sma) / sma * 100
        
        # 8. Above/Below SMA
        features['above_sma'] = (data['close'] > sma).astype(int)
        
        # 9. Cross Up
        features['cross_up'] = ((data['close'] > sma) & (data['close'].shift(1) <= sma.shift(1))).astype(int)
        
        # 10. Cross Down
        features['cross_down'] = ((data['close'] < sma) & (data['close'].shift(1) >= sma.shift(1))).astype(int)
        
        # 11. Volatility adjusted distance
        atr = data['high'].rolling(14, min_periods=1).max() - data['low'].rolling(14, min_periods=1).min()
        features['volatility_adjusted'] = (data['close'] - sma) / (atr + 1e-10)
        
        return features
    
    def validate_params(self, params: Dict) -> None:
        """
        Validiert Parameter.
        
        Args:
            params: Parameter Dictionary
            
        Raises:
            ValueError: Wenn Parameter ungültig
        """
        for param_name, param_info in self.PARAMETERS.items():
            if param_name in params:
                value = params[param_name]
                
                # Type check
                if param_name == 'period' and not isinstance(value, (int, np.integer)):
                    raise ValueError(f"{param_name} must be integer, got {type(value)}")
                
                # Range check
                if 'min' in param_info and value < param_info['min']:
                    raise ValueError(f"{param_name} must be >= {param_info['min']}, got {value}")
                
                if 'max' in param_info and value > param_info['max']:
                    raise ValueError(f"{param_name} must be <= {param_info['max']}, got {value}")
    
    def get_parameter_grid(self) -> Dict:
        """
        Generiert Parameter-Grid für Optimierung.
        
        Returns:
            Dict: Parameter ranges
        """
        grid = {}
        
        for param_name, param_info in self.PARAMETERS.items():
            if param_info.get('optimize', False):
                if 'values' in param_info:
                    grid[param_name] = param_info['values']
                else:
                    grid[param_name] = list(range(
                        param_info['min'],
                        param_info['max'] + 1,
                        param_info['step']
                    ))
        
        return grid
    
    def backtest_vectorbt(
        self, 
        data: pd.DataFrame, 
        params: Dict,
        strategy_type: str = 'fixed',
        init_cash: float = 10000,
        fees: float = 0.0
    ) -> vbt.Portfolio:
        """
        Führt VectorBT Backtest durch.
        
        Args:
            data: OHLCV DataFrame
            params: Parameter Dictionary
            strategy_type: 'fixed' oder 'dynamic'
            init_cash: Initial capital
            fees: Trading fees (0.0 = keine Gebühren)
            
        Returns:
            vbt.Portfolio: Backtest Ergebnis
        """
        if strategy_type == 'fixed':
            signals = self.generate_signals_fixed(data, params)
            
            # VectorBT Portfolio mit TP/SL
            portfolio = vbt.Portfolio.from_signals(
                data['close'],
                entries=signals['entries'],
                exits=signals['exits'],
                tp_stop=signals['tp_levels'],
                sl_stop=signals['sl_levels'],
                freq='30T',
                init_cash=init_cash,
                fees=fees
            )
        else:
            signals = self.generate_signals_dynamic(data, params)
            
            # VectorBT Portfolio ohne TP/SL
            portfolio = vbt.Portfolio.from_signals(
                data['close'],
                entries=signals['entries'],
                exits=signals['exits'],
                freq='30T',
                init_cash=init_cash,
                fees=fees
            )
        
        return portfolio


# Standalone Test
if __name__ == "__main__":
    from datetime import datetime
    
    print("="*80)
    print("SMA INDIKATOR - SINGLE TEST")
    print("="*80)
    
    # Lade EUR/USD 30m 2024-2025 Daten
    try:
        data_path = "c:/Users/nikol/Desktop/Superindikator_Alpha/01_Data/Market_Data/30m/EUR_USD/EUR_USD_aggregated.csv"
        data = pd.read_csv(data_path, index_col='Time', parse_dates=True)
        data.columns = [col.lower() for col in data.columns]
        
        # Filter 2024-2025
        data = data[(data.index >= '2024-01-01') & (data.index < '2025-01-01')]
        
        print(f"\n✅ Daten geladen: {len(data)} Bars (2024-2025)")
        print(f"   Zeitraum: {data.index[0]} bis {data.index[-1]}")
        
    except Exception as e:
        print(f"\n❌ Fehler beim Laden: {e}")
        print("   Erstelle Test-Daten...")
        
        dates = pd.date_range('2024-01-01', '2025-01-01', freq='30T')
        data = pd.DataFrame({
            'open': np.random.randn(len(dates)).cumsum() + 1.1000,
            'high': np.random.randn(len(dates)).cumsum() + 1.1010,
            'low': np.random.randn(len(dates)).cumsum() + 1.0990,
            'close': np.random.randn(len(dates)).cumsum() + 1.1000,
            'volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)
    
    # Initialisiere Indikator
    indicator = Indicator_SMA()
    
    # Test Parameter
    params = {
        'period': 20,
        'tp_pips': 50,
        'sl_pips': 25
    }
    
    print(f"\n📊 TEST PARAMETER:")
    print(f"   Period: {params['period']}")
    print(f"   TP: {params['tp_pips']} pips")
    print(f"   SL: {params['sl_pips']} pips")
    
    # Berechne SMA
    sma = indicator.calculate(data, params)
    print(f"\n✅ SMA berechnet: {len(sma)} Werte")
    
    # Test A.a) Fixed TP/SL
    print(f"\n{'='*80}")
    print("TEST A.a) FIXED TP/SL")
    print("="*80)
    
    signals_fixed = indicator.generate_signals_fixed(data, params)
    print(f"✅ Signale generiert:")
    print(f"   Entries: {signals_fixed['entries'].sum()}")
    print(f"   TP Levels: {signals_fixed['tp_levels'].notna().sum()}")
    print(f"   SL Levels: {signals_fixed['sl_levels'].notna().sum()}")
    
    try:
        portfolio_fixed = indicator.backtest_vectorbt(data, params, 'fixed')
        stats_fixed = portfolio_fixed.stats()
        
        print(f"\n📈 BACKTEST ERGEBNIS (Fixed TP/SL):")
        print(f"   Total Return: {stats_fixed['Total Return [%]']:.2f}%")
        print(f"   Sharpe Ratio: {stats_fixed['Sharpe Ratio']:.2f}")
        print(f"   Max Drawdown: {stats_fixed['Max Drawdown [%]']:.2f}%")
        print(f"   Total Trades: {stats_fixed['Total Trades']}")
        print(f"   Win Rate: {stats_fixed['Win Rate [%]']:.2f}%")
        
    except Exception as e:
        print(f"\n❌ Backtest Fehler: {e}")
    
    # Test A.b) Dynamic Exit
    print(f"\n{'='*80}")
    print("TEST A.b) DYNAMIC EXIT")
    print("="*80)
    
    signals_dynamic = indicator.generate_signals_dynamic(data, params)
    print(f"✅ Signale generiert:")
    print(f"   Entries: {signals_dynamic['entries'].sum()}")
    print(f"   Exits: {signals_dynamic['exits'].sum()}")
    
    try:
        portfolio_dynamic = indicator.backtest_vectorbt(data, params, 'dynamic')
        stats_dynamic = portfolio_dynamic.stats()
        
        print(f"\n📈 BACKTEST ERGEBNIS (Dynamic Exit):")
        print(f"   Total Return: {stats_dynamic['Total Return [%]']:.2f}%")
        print(f"   Sharpe Ratio: {stats_dynamic['Sharpe Ratio']:.2f}")
        print(f"   Max Drawdown: {stats_dynamic['Max Drawdown [%]']:.2f}%")
        print(f"   Total Trades: {stats_dynamic['Total Trades']}")
        print(f"   Win Rate: {stats_dynamic['Win Rate [%]']:.2f}%")
        
    except Exception as e:
        print(f"\n❌ Backtest Fehler: {e}")
    
    # ML Features
    print(f"\n{'='*80}")
    print("ML FEATURES")
    print("="*80)
    
    features = indicator.get_ml_features(data, params)
    print(f"✅ Features extrahiert: {features.shape[1]} Features")
    print(f"   Feature Names: {list(features.columns)}")
    
    print("\n" + "="*80)
    print("SMA TEST ABGESCHLOSSEN ✅")
    print("="*80)
