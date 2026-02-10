#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zenatus Fault-Tolerant Backtesting Engine
Production-grade backtesting system with:
- Connection independence (tmux/systemd safe)
- Real-time monitoring
- Checkpoint/resume logic
- JSON candidate loading per timeframe
- Atomic writes and corruption protection
"""

import os
import sys
import json
import time
import signal
import psutil
import threading
import queue
import uuid
import fcntl
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import argparse
import logging

# Add project path for imports
BASE_PATH = Path("/opt/Zenatus_Backtester")
sys.path.insert(0, str(BASE_PATH))

# Configuration
CONFIG = {
    "base_path": BASE_PATH,
    "data_path": BASE_PATH / "99_Historic_Data",
    "strategies_path": BASE_PATH / "01_Strategy" / "Strategy" / "Full_595" / "All_Strategys",
    "results_base": Path("/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit"),
    "listing_base": Path("/opt/Zenatus_Dokumentation/Listing/Full_backtest"),
    "spreads_path": BASE_PATH / "00_Backtester" / "Spreads",
    "param_opt_path": BASE_PATH / "01_Strategy" / "Parameter_Optimization",
    "checkpoint_interval": 30,  # seconds
    "status_update_interval": 5,  # seconds
    "max_timeout": 1800,  # 30 minutes per strategy
    "atomic_write_temp_suffix": ".tmp",
    "atomic_write_backup_suffix": ".backup"
}

class AtomicFileWriter:
    """Thread-safe atomic file writes with corruption protection"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.temp_path = filepath.with_suffix(filepath.suffix + CONFIG["atomic_write_temp_suffix"])
        self.backup_path = filepath.with_suffix(filepath.suffix + CONFIG["atomic_write_backup_suffix"])
    
    def write_json(self, data: Dict, indent: int = 2) -> bool:
        """Atomically write JSON data"""
        try:
            # Create backup if original exists
            if self.filepath.exists():
                shutil.copy2(self.filepath, self.backup_path)
            
            # Write to temp file
            with open(self.temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename
            self.temp_path.replace(self.filepath)
            
            # Remove backup on success
            if self.backup_path.exists():
                self.backup_path.unlink()
            
            return True
            
        except Exception as e:
            logging.error(f"Atomic write failed for {self.filepath}: {e}")
            # Restore backup if exists
            if self.backup_path.exists():
                shutil.copy2(self.backup_path, self.filepath)
            return False
    
    def read_json(self) -> Optional[Dict]:
        """Safely read JSON with backup fallback"""
        try:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif self.backup_path.exists():
                with open(self.backup_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Read failed for {self.filepath}: {e}")
        return None

class LiveMonitor:
    """Real-time monitoring system with live data updates"""
    
    def __init__(self, session_id: str, timeframe: str):
        self.session_id = session_id
        self.timeframe = timeframe
        self.start_time = datetime.now()
        self.current_strategy = ""
        self.current_strategy_num = 0
        self.total_strategies = 0
        self.tested_combinations = 0
        self.total_combinations = 0
        self.status = "INITIALIZING"
        self.error_state = None
        self.performance_metrics = {
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "daily_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "winrate_pct": 0.0,
            "sharpe_ratio": 0.0,
            "num_trades": 0
        }
        self.monitor_file = CONFIG["results_base"] / timeframe / f"monitor_{session_id}.json"
        self.monitor_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._update_thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start monitoring thread"""
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
    
    def stop(self):
        """Stop monitoring thread"""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=5)
        self._write_monitor_data()
    
    def update_strategy(self, strategy_name: str, strategy_num: int, total_strategies: int):
        """Update current strategy information"""
        with self._lock:
            self.current_strategy = strategy_name
            self.current_strategy_num = strategy_num
            self.total_strategies = total_strategies
    
    def update_combinations(self, tested: int, total: int):
        """Update combination counters"""
        with self._lock:
            self.tested_combinations = tested
            self.total_combinations = total
    
    def update_status(self, status: str, error_state: Optional[str] = None):
        """Update system status"""
        with self._lock:
            self.status = status
            self.error_state = error_state
    
    def update_performance(self, metrics: Dict[str, float]):
        """Update performance metrics"""
        with self._lock:
            self.performance_metrics.update(metrics)
    
    def _update_loop(self):
        """Background update loop"""
        while not self._stop_event.is_set():
            self._write_monitor_data()
            time.sleep(CONFIG["status_update_interval"])
    
    def _write_monitor_data(self):
        """Write monitor data to file"""
        runtime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        data = {
            "session_id": self.session_id,
            "timeframe": self.timeframe,
            "timestamp": datetime.now().isoformat(),
            "runtime_seconds": runtime_seconds,
            "current_strategy": {
                "name": self.current_strategy,
                "number": self.current_strategy_num,
                "total": self.total_strategies
            },
            "combinations": {
                "tested": self.tested_combinations,
                "total": self.total_combinations,
                "progress_pct": (self.tested_combinations / max(self.total_combinations, 1)) * 100
            },
            "status": self.status,
            "error_state": self.error_state,
            "performance_metrics": self.performance_metrics
        }
        
        writer = AtomicFileWriter(self.monitor_file)
        writer.write_json(data)

class CheckpointManager:
    """Manages checkpoints with atomic writes and resume logic"""
    
    def __init__(self, session_id: str, timeframe: str):
        self.session_id = session_id
        self.timeframe = timeframe
        self.checkpoint_dir = CONFIG["results_base"] / timeframe / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"checkpoint_{session_id}.json"
        self.completed_strategies = set()
        self.current_strategy = None
        self._lock = threading.Lock()
    
    def load_checkpoint(self) -> Dict:
        """Load existing checkpoint data"""
        writer = AtomicFileWriter(self.checkpoint_file)
        data = writer.read_json()
        
        if data:
            self.completed_strategies = set(data.get("completed_strategies", []))
            self.current_strategy = data.get("current_strategy")
            return data
        
        return {
            "session_id": self.session_id,
            "timeframe": self.timeframe,
            "completed_strategies": [],
            "current_strategy": None,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
    
    def is_strategy_completed(self, strategy_name: str) -> bool:
        """Check if strategy is already completed"""
        with self._lock:
            return strategy_name in self.completed_strategies
    
    def mark_strategy_completed(self, strategy_name: str):
        """Mark strategy as completed with atomic write"""
        with self._lock:
            self.completed_strategies.add(strategy_name)
            self.current_strategy = None
            self._save_checkpoint()
    
    def set_current_strategy(self, strategy_name: str):
        """Set current strategy being processed"""
        with self._lock:
            self.current_strategy = strategy_name
            self._save_checkpoint()
    
    def _save_checkpoint(self):
        """Save checkpoint data atomically"""
        data = {
            "session_id": self.session_id,
            "timeframe": self.timeframe,
            "completed_strategies": list(self.completed_strategies),
            "current_strategy": self.current_strategy,
            "start_time": self.load_checkpoint().get("start_time", datetime.now().isoformat()),
            "last_update": datetime.now().isoformat()
        }
        
        writer = AtomicFileWriter(self.checkpoint_file)
        writer.write_json(data)

class StrategyLoader:
    """Loads strategies from JSON candidate lists per timeframe"""
    
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.candidate_file = CONFIG["listing_base"] / timeframe / f"candidates_{timeframe}.json"
        
        # Fallback to existing files if candidates.json doesn't exist
        self.status_files = {
            "working": CONFIG["listing_base"] / timeframe / "indicators_working.json",
            "successful": CONFIG["listing_base"] / timeframe / "indicators_succesful_backtested.json",
            "warning": CONFIG["listing_base"] / timeframe / "indicators_warnings.json",
            "error": CONFIG["listing_base"] / timeframe / "indicators_errors.json",
            "timeout": CONFIG["listing_base"] / timeframe / "indicators_timeout.json",
            "no_results": CONFIG["listing_base"] / timeframe / "indicators_no_results.json"
        }
    
    def load_candidates(self, status_filter: Optional[List[str]] = None) -> List[str]:
        """Load strategy candidates from JSON files"""
        candidates = []
        
        # Try primary candidate file first
        if self.candidate_file.exists():
            try:
                with open(self.candidate_file, 'r') as f:
                    data = json.load(f)
                    candidates = data.get("strategies", [])
                    logging.info(f"Loaded {len(candidates)} candidates from {self.candidate_file}")
                    return candidates
            except Exception as e:
                logging.warning(f"Failed to load candidates from {self.candidate_file}: {e}")
        
        # Fallback to status-based files
        if status_filter is None:
            status_filter = ["working"]  # Default to working strategies
        
        for status in status_filter:
            file_path = self.status_files.get(status.lower())
            if file_path and file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        strategies = data.get("scripts", [])
                        candidates.extend(strategies)
                        logging.info(f"Loaded {len(strategies)} {status} strategies")
                except Exception as e:
                    logging.warning(f"Failed to load {status} strategies: {e}")
        
        return list(set(candidates))  # Remove duplicates

class BacktestEngine:
    """Main backtesting engine with fault tolerance"""
    
    def __init__(self, timeframe: str, session_id: str):
        self.timeframe = timeframe
        self.session_id = session_id
        self.monitor = LiveMonitor(session_id, timeframe)
        self.checkpoint = CheckpointManager(session_id, timeframe)
        self.strategy_loader = StrategyLoader(timeframe)
        self.running = False
        self.current_process = None
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for the engine"""
        log_dir = CONFIG["results_base"] / self.timeframe / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"engine_{self.session_id}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def run(self, strategies: List[str], symbols: List[str], start_date: str, end_date: str, capital: float):
        """Run backtesting with fault tolerance"""
        self.running = True
        self.monitor.start()
        
        # Load checkpoint data
        checkpoint_data = self.checkpoint.load_checkpoint()
        completed_count = len(checkpoint_data.get("completed_strategies", []))
        
        logging.info(f"Starting backtest session {self.session_id}")
        logging.info(f"Timeframe: {self.timeframe}, Strategies: {len(strategies)}, Completed: {completed_count}")
        
        self.monitor.update_status("RUNNING")
        self.monitor.update_strategy("", 0, len(strategies))
        
        try:
            for i, strategy in enumerate(strategies, 1):
                if not self.running:
                    break
                
                # Skip if already completed
                if self.checkpoint.is_strategy_completed(strategy):
                    logging.info(f"Skipping completed strategy: {strategy}")
                    continue
                
                # Set current strategy in checkpoint
                self.checkpoint.set_current_strategy(strategy)
                
                # Update monitor
                self.monitor.update_strategy(strategy, i, len(strategies))
                self.monitor.update_status("PROCESSING_STRATEGY")
                
                # Run strategy backtest
                success = self._run_strategy(strategy, symbols, start_date, end_date, capital)
                
                if success:
                    self.checkpoint.mark_strategy_completed(strategy)
                    self.monitor.update_status("STRATEGY_COMPLETED")
                else:
                    self.monitor.update_status("STRATEGY_FAILED", f"Strategy {strategy} failed")
                
                # Small delay between strategies
                time.sleep(1)
            
            self.monitor.update_status("SESSION_COMPLETED")
            logging.info(f"Backtest session {self.session_id} completed")
            
        except Exception as e:
            self.monitor.update_status("SESSION_FAILED", str(e))
            logging.error(f"Session failed: {e}")
        
        finally:
            self.monitor.stop()
            self.running = False
    
    def _run_strategy(self, strategy: str, symbols: List[str], start_date: str, end_date: str, capital: float) -> bool:
        """Run individual strategy backtest"""
        try:
            logging.info(f"Processing strategy: {strategy}")
            
            # Build command for the existing worker script
            cmd = [
                sys.executable,
                str(CONFIG["base_path"] / "00_Backtester" / "Start_Backtesting_Scripts" / "Full_Backtest" / "Fixed_Exit" / "1h" / "FULL_BACKTEST_1H_WORKER.py"),
                "--scripts", strategy,
                "--timeframe", self.timeframe,
                "--symbols", ",".join(symbols),
                "--start-date", start_date,
                "--end-date", end_date,
                "--capital", str(capital),
                "--worker-id", "0"
            ]
            
            # Run strategy with timeout
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  # Detach from parent process
            )
            
            # Monitor process
            try:
                stdout, stderr = self.current_process.communicate(timeout=CONFIG["max_timeout"])
                
                if self.current_process.returncode == 0:
                    logging.info(f"Strategy {strategy} completed successfully")
                    return True
                else:
                    logging.error(f"Strategy {strategy} failed with return code {self.current_process.returncode}")
                    logging.error(f"STDERR: {stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                self.current_process.kill()
                logging.error(f"Strategy {strategy} timed out after {CONFIG['max_timeout']} seconds")
                return False
            
        except Exception as e:
            logging.error(f"Error running strategy {strategy}: {e}")
            return False
        
        finally:
            self.current_process = None
    
    def stop(self):
        """Stop the engine gracefully"""
        self.running = False
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=10)
            except:
                self.current_process.kill()
        
        self.monitor.stop()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    if 'engine' in globals():
        engine.stop()
    sys.exit(0)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Zenatus Fault-Tolerant Backtesting Engine")
    parser.add_argument("--timeframe", required=True, help="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, default=10000.0, help="Starting capital")
    parser.add_argument("--status-filter", default="working", help="Strategy status filter (working,successful,warning,error,timeout,no_results)")
    parser.add_argument("--session-id", help="Session ID (auto-generated if not provided)")
    
    args = parser.parse_args()
    
    # Generate session ID if not provided
    session_id = args.session_id or str(uuid.uuid4())[:8]
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.info(f"Starting Zenatus Backtesting Engine")
    logging.info(f"Session ID: {session_id}")
    logging.info(f"Timeframe: {args.timeframe}")
    logging.info(f"Symbols: {args.symbols}")
    
    # Create engine
    engine = BacktestEngine(args.timeframe, session_id)
    globals()['engine'] = engine
    
    # Load strategy candidates
    status_filter = args.status_filter.split(',') if args.status_filter else ["working"]
    strategy_loader = StrategyLoader(args.timeframe)
    strategies = strategy_loader.load_candidates(status_filter)
    
    if not strategies:
        logging.error("No strategies found for the specified criteria")
        return 1
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    # Run backtest
    engine.run(strategies, symbols, args.start_date, args.end_date, args.capital)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())