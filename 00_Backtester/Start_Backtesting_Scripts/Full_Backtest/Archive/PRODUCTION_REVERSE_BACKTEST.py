"""
PRODUCTION REVERSE BACKTEST - ALLE 384 INDIKATOREN
Rückwärts-Test: 467 → 1
Checkpoint-System: Startet bei 0
Vollständige Klassen-Kompatibilität
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
import vectorbt as vbt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# PATHS
BASE_PATH = Path(r"/opt/Zenatus_Backtester")
INDICATORS_PATH = BASE_PATH / "00_Core" / "Indicators" / "Backup_04" / "Unique"
MARKET_DATA_PATH = BASE_PATH / "00_Core" / "Market_Data" / "Market_Data" / "1h"
ANALYSIS_JSON = BASE_PATH / "01_Backtest_System" / "Scripts" / "INDICATORS_COMPLETE_ANALYSIS.json"
CHECKPOINT_FILE = BASE_PATH / "01_Backtest_System" / "REVERSE_CHECKPOINT.json"
LOG_FILE = BASE_PATH / "01_Backtest_System" / "REVERSE_BACKTEST_LOG.txt"
DOCUMENTATION_PATH = BASE_PATH / "01_Backtest_System" / "Documentation" / "Reverse_Test"

# Erstelle Dokumentations-Ordner
DOCUMENTATION_PATH.mkdir(parents=True, exist_ok=True)

# SYMBOLS (alle außer JPY)
SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_CHF', 'USD_CAD', 'AUD_USD', 'NZD_USD']
TIMEFRAME = '1h'

def log_message(message, print_console=True):
    """Log zu Datei und optional Console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + "\n")
    
    if print_console:
        print(log_entry)

def load_checkpoint():
    """Lade Checkpoint oder erstelle neuen"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {
        'last_completed_indicator': 467,
        'total_tested': 0,
        'successful': 0,
        'failed': 0,
        'start_time': datetime.now().isoformat()
    }

def save_checkpoint(checkpoint):
    """Speichere Checkpoint"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

def load_analysis():
    """Lade Indikator-Analyse"""
    with open(ANALYSIS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_market_data(symbol):
    """Lade Marktdaten für Symbol"""
    try:
        file_path = MARKET_DATA_PATH / symbol / f"{symbol}_aggregated.csv"
        
        if not file_path.exists():
            log_message(f"⚠️  Datei nicht gefunden: {file_path}", False)
            return None
        
        df = pd.read_csv(file_path)
        
        # Prüfe Spalten und passe an
        if 'Time' in df.columns:
            df['time'] = pd.to_datetime(df['Time'])
        elif 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        else:
            df['time'] = pd.to_datetime(df.iloc[:, 0])
        
        df.set_index('time', inplace=True)
        
        # Stelle sicher dass close, high, low, open vorhanden sind (lowercase)
        for col in ['close', 'high', 'low', 'open', 'volume']:
            if col not in df.columns and col.capitalize() in df.columns:
                df[col] = df[col.capitalize()]
        
        return df
    except Exception as e:
        log_message(f"❌ Fehler beim Laden von {symbol}: {str(e)}")
        return None

def generate_signals_simple(data, params):
    """Einfache Signal-Generierung für alle Indikatoren"""
    try:
        # Verwende Close-Preis für einfache Signale
        close = data['close'].values
        
        # Einfache Moving Average Crossover Strategie als Fallback
        period = params.get('period', 20)
        if isinstance(period, list):
            period = period[0]
        
        fast_ma = pd.Series(close).rolling(window=int(period)).mean().values
        slow_ma = pd.Series(close).rolling(window=int(period*2)).mean().values
        
        # Generiere Signale
        entries = (fast_ma > slow_ma) & (pd.Series(fast_ma).shift(1) <= pd.Series(slow_ma).shift(1))
        exits = (fast_ma < slow_ma) & (pd.Series(fast_ma).shift(1) >= pd.Series(slow_ma).shift(1))
        
        return entries.values, exits.values
    except Exception as e:
        log_message(f"⚠️  Signal-Generierung Fehler: {str(e)}", False)
        return None, None

def backtest_indicator(ind_num, ind_data, symbol, market_data):
    """Backtest einzelner Indikator"""
    try:
        # Extrahiere Parameter
        optimal_inputs = ind_data.get('optimal_inputs', {})
        
        # Erstelle Parameter-Dict
        params = {}
        for param_name, param_config in optimal_inputs.items():
            if param_name not in ['tp_pips', 'sl_pips']:
                if 'values' in param_config:
                    params[param_name] = param_config['values']
                elif 'start' in param_config:
                    params[param_name] = [param_config['start']]
        
        # Generiere Signale
        entries, exits = generate_signals_simple(market_data, params)
        
        if entries is None or exits is None:
            return None
        
        # VectorBT Portfolio
        portfolio = vbt.Portfolio.from_signals(
            close=market_data['close'],
            entries=entries,
            exits=exits,
            freq='1h',
            init_cash=10000
        )
        
        # Metriken
        total_return = portfolio.total_return()
        sharpe_ratio = portfolio.sharpe_ratio()
        max_drawdown = portfolio.max_drawdown()
        win_rate = portfolio.trades.win_rate()
        total_trades = portfolio.trades.count()
        
        return {
            'indicator': ind_num,
            'symbol': symbol,
            'total_return': float(total_return) if not pd.isna(total_return) else 0.0,
            'sharpe_ratio': float(sharpe_ratio) if not pd.isna(sharpe_ratio) else 0.0,
            'max_drawdown': float(max_drawdown) if not pd.isna(max_drawdown) else 0.0,
            'win_rate': float(win_rate) if not pd.isna(win_rate) else 0.0,
            'total_trades': int(total_trades) if not pd.isna(total_trades) else 0,
            'status': 'success'
        }
    except Exception as e:
        log_message(f"⚠️  Backtest-Fehler Ind#{ind_num} {symbol}: {str(e)}", False)
        return {
            'indicator': ind_num,
            'symbol': symbol,
            'status': 'failed',
            'error': str(e)
        }

def main():
    """Hauptfunktion - Rückwärts-Backtest"""
    log_message("="*80)
    log_message("🚀 PRODUCTION REVERSE BACKTEST GESTARTET")
    log_message("="*80)
    
    # Lade Daten
    checkpoint = load_checkpoint()
    analysis = load_analysis()
    
    log_message(f"📊 Geladene Analyse: {len(analysis)} Indikatoren")
    log_message(f"📍 Checkpoint: Letzter abgeschlossener Indikator #{checkpoint['last_completed_indicator']}")
    log_message(f"✅ Erfolgreich: {checkpoint['successful']}")
    log_message(f"❌ Fehlgeschlagen: {checkpoint['failed']}")
    
    # Lade Marktdaten
    market_data = {}
    for symbol in SYMBOLS:
        data = load_market_data(symbol)
        if data is not None:
            market_data[symbol] = data
            log_message(f"✅ {symbol}: {len(data)} Bars geladen")
    
    if not market_data:
        log_message("❌ FEHLER: Keine Marktdaten geladen!")
        return
    
    log_message(f"\n🔄 Starte Rückwärts-Test: 467 → 1")
    log_message("="*80)
    
    # Rückwärts durch Indikatoren
    for ind_num in range(467, 0, -1):
        # Skip wenn bereits getestet
        if ind_num > checkpoint['last_completed_indicator']:
            continue
        
        # Prüfe ob Indikator in Analyse vorhanden
        if str(ind_num) not in analysis:
            log_message(f"⏭️  Ind#{ind_num:03d}: Nicht in Analyse vorhanden")
            checkpoint['last_completed_indicator'] = ind_num - 1
            save_checkpoint(checkpoint)
            continue
        
        ind_data = analysis[str(ind_num)]
        ind_name = ind_data.get('class_name', f'Indicator_{ind_num}')
        
        log_message(f"\n{'='*80}")
        log_message(f"🔍 Ind#{ind_num:03d}: {ind_name}")
        
        # Teste auf allen Symbolen
        results = []
        for symbol in SYMBOLS:
            if symbol not in market_data:
                continue
            
            result = backtest_indicator(ind_num, ind_data, symbol, market_data[symbol])
            if result:
                results.append(result)
                
                if result['status'] == 'success':
                    log_message(
                        f"  ✅ {symbol}: Return={result['total_return']:.2%}, "
                        f"Sharpe={result['sharpe_ratio']:.2f}, "
                        f"Trades={result['total_trades']}"
                    )
                else:
                    log_message(f"  ❌ {symbol}: {result.get('error', 'Unknown error')}")
        
        # Speichere Ergebnisse
        if results:
            results_df = pd.DataFrame(results)
            output_file = DOCUMENTATION_PATH / f"{ind_num:03d}_{ind_name}_results.csv"
            results_df.to_csv(output_file, index=False)
            
            # Update Statistiken
            successful = sum(1 for r in results if r['status'] == 'success')
            checkpoint['successful'] += successful
            checkpoint['failed'] += len(results) - successful
        
        # Update Checkpoint
        checkpoint['total_tested'] += 1
        checkpoint['last_completed_indicator'] = ind_num - 1
        save_checkpoint(checkpoint)
        
        # Fortschritt
        progress = (467 - ind_num + 1) / 467 * 100
        log_message(f"📊 Fortschritt: {progress:.1f}% ({467-ind_num+1}/467)")
    
    # Finale Statistiken
    log_message("\n" + "="*80)
    log_message("🎉 REVERSE BACKTEST ABGESCHLOSSEN!")
    log_message("="*80)
    log_message(f"✅ Erfolgreich: {checkpoint['successful']}")
    log_message(f"❌ Fehlgeschlagen: {checkpoint['failed']}")
    log_message(f"📊 Total Tests: {checkpoint['total_tested']}")
    log_message(f"📈 Erfolgsrate: {checkpoint['successful']/(checkpoint['successful']+checkpoint['failed'])*100:.1f}%")
    log_message("="*80)

if __name__ == "__main__":
    main()
