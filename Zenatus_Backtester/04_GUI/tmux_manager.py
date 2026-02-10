#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zenatus tmux Session Manager
Manages persistent backtesting sessions with connection independence
"""

import os
import sys
import subprocess
import time
import argparse
import json
from pathlib import Path

TMUX_SESSION_PREFIX = "zenatus_backtest_"
BASE_PATH = Path("/opt/Zenatus_Backtester")
ENGINE_SCRIPT = BASE_PATH / "04_GUI" / "engine.py"
MONITOR_SCRIPT = BASE_PATH / "04_GUI" / "monitor.py"

def run_command(cmd, check=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode

def is_tmux_installed():
    """Check if tmux is installed"""
    stdout, stderr, code = run_command("which tmux", check=False)
    return code == 0

def get_active_sessions():
    """Get list of active tmux sessions"""
    stdout, stderr, code = run_command("tmux list-sessions 2>/dev/null", check=False)
    if code != 0:
        return []
    
    sessions = []
    for line in stdout.split('\n'):
        if line.strip():
            parts = line.split(':')
            if len(parts) >= 1:
                session_name = parts[0].strip()
                if session_name.startswith(TMUX_SESSION_PREFIX):
                    sessions.append(session_name)
    return sessions

def create_session(session_name: str, command: str, detach: bool = True):
    """Create new tmux session"""
    detach_flag = "-d" if detach else ""
    full_cmd = f"tmux new-session {detach_flag} -s {session_name} '{command}'"
    stdout, stderr, code = run_command(full_cmd, check=False)
    return code == 0, stdout, stderr

def attach_session(session_name: str):
    """Attach to existing tmux session"""
    cmd = f"tmux attach-session -t {session_name}"
    os.system(cmd)

def kill_session(session_name: str):
    """Kill tmux session"""
    cmd = f"tmux kill-session -t {session_name}"
    stdout, stderr, code = run_command(cmd, check=False)
    return code == 0

def get_session_info(session_name: str):
    """Get detailed session information"""
    cmd = f"tmux list-panes -t {session_name} -F '#{{pane_current_command}} #{{pane_pid}}'"
    stdout, stderr, code = run_command(cmd, check=False)
    
    if code != 0:
        return None
    
    lines = stdout.strip().split('\n')
    if not lines or not lines[0].strip():
        return None
    
    # Parse process info
    parts = lines[0].split()
    if len(parts) >= 2:
        return {
            "command": parts[0],
            "pid": int(parts[1]) if parts[1].isdigit() else 0,
            "session_name": session_name
        }
    
    return None

def is_process_running(pid: int) -> bool:
    """Check if process is running"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def start_backtest_session(timeframe: str, symbols: str, start_date: str, end_date: str, 
                          capital: float = 10000.0, status_filter: str = "working"):
    """Start a new backtesting session"""
    session_name = f"{TMUX_SESSION_PREFIX}{timeframe}_{int(time.time())}"
    
    # Build command
    cmd = f"cd {BASE_PATH} && python3 {ENGINE_SCRIPT} "
    cmd += f"--timeframe {timeframe} "
    cmd += f"--symbols {symbols} "
    cmd += f"--start-date {start_date} "
    cmd += f"--end-date {end_date} "
    cmd += f"--capital {capital} "
    cmd += f"--status-filter {status_filter}"
    
    success, stdout, stderr = create_session(session_name, cmd)
    
    if success:
        return session_name, f"Session {session_name} started successfully"
    else:
        return None, f"Failed to start session: {stderr}"

def start_monitor_session(timeframe: str):
    """Start monitoring session"""
    session_name = f"{TMUX_SESSION_PREFIX}monitor_{timeframe}_{int(time.time())}"
    
    cmd = f"cd {BASE_PATH} && python3 {MONITOR_SCRIPT} --timeframe {timeframe}"
    
    success, stdout, stderr = create_session(session_name, cmd)
    
    if success:
        return session_name, f"Monitor {session_name} started"
    else:
        return None, f"Failed to start monitor: {stderr}"

def list_sessions():
    """List all active sessions with status"""
    sessions = get_active_sessions()
    
    if not sessions:
        return "No active tmux sessions found"
    
    result = []
    result.append("Active Zenatus Sessions:")
    result.append("=" * 50)
    
    for session in sessions:
        info = get_session_info(session)
        if info:
            pid = info.get("pid", 0)
            is_running = is_process_running(pid) if pid > 0 else False
            status = "RUNNING" if is_running else "STOPPED"
            
            result.append(f"Session: {session}")
            result.append(f"  PID: {pid}")
            result.append(f"  Status: {status}")
            result.append(f"  Command: {info.get('command', 'Unknown')}")
            result.append("")
        else:
            result.append(f"Session: {session} (Info unavailable)")
            result.append("")
    
    return "\n".join(result)

def stop_all_sessions():
    """Stop all zenatus sessions"""
    sessions = get_active_sessions()
    stopped = 0
    
    for session in sessions:
        if kill_session(session):
            stopped += 1
    
    return f"Stopped {stopped} sessions"

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Zenatus tmux Session Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check tmux
    parser.add_argument("--check-tmux", action="store_true", help="Check if tmux is installed")
    
    # Start backtest
    start_parser = subparsers.add_parser("start", help="Start new backtesting session")
    start_parser.add_argument("--timeframe", required=True, help="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)")
    start_parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    start_parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    start_parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    start_parser.add_argument("--capital", type=float, default=10000.0, help="Starting capital")
    start_parser.add_argument("--status-filter", default="working", help="Strategy status filter")
    
    # Start monitor
    monitor_parser = subparsers.add_parser("monitor", help="Start monitoring session")
    monitor_parser.add_argument("--timeframe", required=True, help="Timeframe to monitor")
    
    # List sessions
    list_parser = subparsers.add_parser("list", help="List active sessions")
    
    # Stop sessions
    stop_parser = subparsers.add_parser("stop", help="Stop sessions")
    stop_parser.add_argument("--all", action="store_true", help="Stop all sessions")
    stop_parser.add_argument("--session", help="Specific session to stop")
    
    # Attach to session
    attach_parser = subparsers.add_parser("attach", help="Attach to session")
    attach_parser.add_argument("session", help="Session name to attach to")
    
    args = parser.parse_args()
    
    # Check tmux installation
    if not is_tmux_installed():
        print("Error: tmux is not installed. Please install tmux first.")
        print("Run: apt-get install tmux")
        return 1
    
    if args.check_tmux:
        print("tmux is installed and available")
        return 0
    
    # Handle commands
    if args.command == "start":
        session_name, message = start_backtest_session(
            args.timeframe, args.symbols, args.start_date, args.end_date,
            args.capital, args.status_filter
        )
        print(message)
        if session_name:
            print(f"To attach: python3 {sys.argv[0]} attach {session_name}")
            print(f"To monitor: python3 {sys.argv[0]} monitor --timeframe {args.timeframe}")
    
    elif args.command == "monitor":
        session_name, message = start_monitor_session(args.timeframe)
        print(message)
        if session_name:
            print(f"To attach: python3 {sys.argv[0]} attach {session_name}")
    
    elif args.command == "list":
        print(list_sessions())
    
    elif args.command == "stop":
        if args.all:
            result = stop_all_sessions()
            print(result)
        elif args.session:
            if kill_session(args.session):
                print(f"Session {args.session} stopped")
            else:
                print(f"Failed to stop session {args.session}")
        else:
            print("Please specify --all or --session")
    
    elif args.command == "attach":
        attach_session(args.session)
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())