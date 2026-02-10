#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zenatus Live Monitoring Dashboard
Real-time monitoring for backtesting sessions
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import curses
import threading
import queue

# Configuration
BASE_PATH = Path("/opt/Zenatus_Backtester")
RESULTS_BASE = Path("/opt/Zenatus_Dokumentation/Dokumentation/Fixed_Exit")

class LiveMonitorDashboard:
    """Terminal-based live monitoring dashboard"""
    
    def __init__(self, timeframe: str = "1h", refresh_rate: float = 1.0):
        self.timeframe = timeframe
        self.refresh_rate = refresh_rate
        self.running = True
        self.screen = None
        self.monitor_files = []
        self.session_data = {}
        self.update_queue = queue.Queue()
    
    def find_sessions(self):
        """Find all active monitoring sessions"""
        monitor_dir = RESULTS_BASE / self.timeframe
        if not monitor_dir.exists():
            return []
        
        # Look for monitor files
        monitor_files = list(monitor_dir.glob("monitor_*.json"))
        
        # Filter for recent files (last 24 hours)
        recent_files = []
        for file in monitor_files:
            try:
                stat = file.stat()
                if time.time() - stat.st_mtime < 86400:  # 24 hours
                    recent_files.append(file)
            except:
                pass
        
        return recent_files
    
    def load_session_data(self, file_path):
        """Load data from a single session file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                data['file_path'] = str(file_path)
                data['last_seen'] = time.time()
                return data
        except Exception as e:
            return {
                "session_id": file_path.stem.replace("monitor_", ""),
                "timeframe": self.timeframe,
                "error": f"Failed to load: {e}",
                "last_seen": time.time()
            }
    
    def update_sessions(self):
        """Update all session data"""
        current_files = self.find_sessions()
        
        # Remove old sessions
        current_paths = {str(f) for f in current_files}
        for path in list(self.session_data.keys()):
            if path not in current_paths:
                del self.session_data[path]
        
        # Update existing and add new
        for file_path in current_files:
            path_str = str(file_path)
            self.session_data[path_str] = self.load_session_data(file_path)
    
    def format_time(self, seconds):
        """Format seconds to human readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds/3600)
            minutes = int((seconds%3600)/60)
            return f"{hours}h {minutes}m"
    
    def format_percentage(self, value, total):
        """Format percentage"""
        if total == 0:
            return "0.0%"
        return f"{(value/total)*100:.1f}%"
    
    def draw_dashboard(self, stdscr):
        """Main dashboard drawing function"""
        self.screen = stdscr
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)  # Non-blocking input
        stdscr.timeout(int(self.refresh_rate * 1000))  # Refresh rate in ms
        
        # Colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        
        while self.running:
            try:
                stdscr.clear()
                height, width = stdscr.getmaxyx()
                
                # Header
                header = f" Zenatus Backtesting Monitor - {self.timeframe.upper()} "
                stdscr.addstr(0, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(4))
                stdscr.addstr(1, 0, "=" * width, curses.color_pair(4))
                
                # Update sessions
                self.update_sessions()
                
                if not self.session_data:
                    stdscr.addstr(3, 2, "No active sessions found", curses.color_pair(3))
                    stdscr.addstr(4, 2, f"Monitoring: {RESULTS_BASE / self.timeframe}", curses.color_pair(5))
                else:
                    row = 3
                    for path, data in self.session_data.items():
                        if row >= height - 3:  # Leave space for footer
                            break
                        
                        session_id = data.get("session_id", "Unknown")
                        status = data.get("status", "UNKNOWN")
                        
                        # Session header
                        color = self.get_status_color(status)
                        stdscr.addstr(row, 2, f"Session: {session_id}", curses.A_BOLD | color)
                        stdscr.addstr(row, 40, f"Status: {status}", color)
                        row += 1
                        
                        # Runtime
                        runtime = data.get("runtime_seconds", 0)
                        stdscr.addstr(row, 4, f"Runtime: {self.format_time(runtime)}", curses.color_pair(5))
                        row += 1
                        
                        # Current strategy
                        current = data.get("current_strategy", {})
                        if current:
                            strategy_name = current.get("name", "None")
                            strategy_num = current.get("number", 0)
                            total_strategies = current.get("total", 0)
                            
                            stdscr.addstr(row, 4, f"Strategy: {strategy_name}", curses.color_pair(2))
                            if total_strategies > 0:
                                progress = self.format_percentage(strategy_num, total_strategies)
                                stdscr.addstr(row, 50, f"Progress: {strategy_num}/{total_strategies} ({progress})", curses.color_pair(1))
                            row += 1
                        
                        # Combinations
                        combinations = data.get("combinations", {})
                        if combinations:
                            tested = combinations.get("tested", 0)
                            total = combinations.get("total", 0)
                            progress_pct = combinations.get("progress_pct", 0)
                            
                            stdscr.addstr(row, 4, f"Combinations: {tested}/{total}", curses.color_pair(5))
                            stdscr.addstr(row, 40, f"({progress_pct:.1f}%)", curses.color_pair(1))
                            row += 1
                        
                        # Performance metrics
                        metrics = data.get("performance_metrics", {})
                        if metrics:
                            stdscr.addstr(row, 4, "Performance:", curses.A_BOLD)
                            row += 1
                            
                            # First row of metrics
                            return_pct = metrics.get("return_pct", 0)
                            max_dd = metrics.get("max_drawdown_pct", 0)
                            winrate = metrics.get("winrate_pct", 0)
                            
                            stdscr.addstr(row, 6, f"Return: {return_pct:.2f}%", curses.color_pair(1 if return_pct >= 0 else 3))
                            stdscr.addstr(row, 25, f"Max DD: {max_dd:.2f}%", curses.color_pair(3 if max_dd > 5 else 2))
                            stdscr.addstr(row, 45, f"Winrate: {winrate:.1f}%", curses.color_pair(1 if winrate > 50 else 3))
                            row += 1
                            
                            # Second row of metrics
                            profit_factor = metrics.get("profit_factor", 0)
                            sharpe = metrics.get("sharpe_ratio", 0)
                            num_trades = metrics.get("num_trades", 0)
                            
                            stdscr.addstr(row, 6, f"PF: {profit_factor:.2f}", curses.color_pair(1 if profit_factor > 1 else 3))
                            stdscr.addstr(row, 25, f"Sharpe: {sharpe:.2f}", curses.color_pair(1 if sharpe > 0 else 3))
                            stdscr.addstr(row, 45, f"Trades: {num_trades}", curses.color_pair(5))
                            row += 1
                        
                        # Error state
                        error = data.get("error_state")
                        if error:
                            stdscr.addstr(row, 4, f"Error: {error}", curses.color_pair(3))
                            row += 1
                        
                        row += 1  # Space between sessions
                
                # Footer
                if height > 5:
                    stdscr.addstr(height-2, 0, "=" * width, curses.color_pair(4))
                    footer = f"Press 'q' to quit | Refresh: {self.refresh_rate}s | {datetime.now().strftime('%H:%M:%S')}"
                    stdscr.addstr(height-1, 2, footer, curses.color_pair(5))
                
                stdscr.refresh()
                
                # Handle input
                try:
                    key = stdscr.getch()
                    if key == ord('q') or key == ord('Q'):
                        self.running = False
                        break
                    elif key == ord('r') or key == ord('R'):
                        self.update_sessions()
                except:
                    pass
                    
            except Exception as e:
                try:
                    stdscr.clear()
                    stdscr.addstr(2, 2, f"Error: {e}", curses.color_pair(3))
                    stdscr.refresh()
                    time.sleep(2)
                except:
                    pass
    
    def get_status_color(self, status):
        """Get color for status"""
        status = status.upper()
        if status in ["RUNNING", "SUCCESS", "COMPLETED"]:
            return curses.color_pair(1)  # Green
        elif status in ["WARNING", "PROCESSING_STRATEGY", "STRATEGY_COMPLETED"]:
            return curses.color_pair(2)  # Yellow
        elif status in ["ERROR", "FAILED", "TIMEOUT"]:
            return curses.color_pair(3)  # Red
        else:
            return curses.color_pair(5)  # White
    
    def run(self):
        """Run the dashboard"""
        try:
            curses.wrapper(self.draw_dashboard)
        except KeyboardInterrupt:
            self.running = False
        except Exception as e:
            print(f"Dashboard error: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Zenatus Live Monitoring Dashboard")
    parser.add_argument("--timeframe", default="1h", help="Timeframe to monitor (1m, 5m, 15m, 30m, 1h, 4h, 1d)")
    parser.add_argument("--refresh-rate", type=float, default=1.0, help="Refresh rate in seconds")
    
    args = parser.parse_args()
    
    dashboard = LiveMonitorDashboard(args.timeframe, args.refresh_rate)
    dashboard.run()

if __name__ == "__main__":
    main()