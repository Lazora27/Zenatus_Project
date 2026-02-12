#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zenatus Production Service Manager
Manages systemd services for fault-tolerant backtesting
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

SERVICE_NAME = "zenatus-backtest"
SERVICE_FILE = f"/etc/systemd/system/{SERVICE_NAME}.service"
BASE_PATH = Path("/opt/Zenatus_Backtester")
ENGINE_SCRIPT = BASE_PATH / "04_GUI" / "engine.py"

def run_command(cmd, check=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode

def is_systemd_available():
    """Check if systemd is available"""
    stdout, stderr, code = run_command("which systemctl", check=False)
    return code == 0

def create_service_file(timeframe: str, symbols: str, start_date: str, end_date: str, 
                       capital: float = 10000.0, status_filter: str = "working"):
    """Create systemd service file"""
    service_content = f"""[Unit]
Description=Zenatus Backtesting Engine - {timeframe.upper()}
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory={BASE_PATH}
ExecStart=/usr/bin/python3 {ENGINE_SCRIPT} --timeframe {timeframe} --symbols {symbols} --start-date {start_date} --end-date {end_date} --capital {capital} --status-filter {status_filter}
Restart=always
RestartSec=30
StandardOutput=append:/var/log/zenatus_backtest_{timeframe}.log
StandardError=append:/var/log/zenatus_backtest_{timeframe}.log
Environment=PYTHONUNBUFFERED=1

# Security
NoNewPrivileges=false
PrivateTmp=false
ProtectSystem=false

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open(SERVICE_FILE, 'w') as f:
            f.write(service_content)
        return True
    except Exception as e:
        print(f"Error creating service file: {e}")
        return False

def enable_service():
    """Enable and start the service"""
    commands = [
        "systemctl daemon-reload",
        f"systemctl enable {SERVICE_NAME}",
        f"systemctl start {SERVICE_NAME}"
    ]
    
    for cmd in commands:
        stdout, stderr, code = run_command(cmd, check=False)
        if code != 0:
            print(f"Command failed: {cmd}")
            print(f"Error: {stderr}")
            return False
    
    return True

def disable_service():
    """Stop and disable the service"""
    commands = [
        f"systemctl stop {SERVICE_NAME}",
        f"systemctl disable {SERVICE_NAME}"
    ]
    
    for cmd in commands:
        stdout, stderr, code = run_command(cmd, check=False)
        if code != 0:
            print(f"Command failed: {cmd}")
            print(f"Error: {stderr}")
    
    return True

def remove_service_file():
    """Remove the service file"""
    if os.path.exists(SERVICE_FILE):
        try:
            os.remove(SERVICE_FILE)
            return True
        except Exception as e:
            print(f"Error removing service file: {e}")
            return False
    return True

def get_service_status():
    """Get service status"""
    stdout, stderr, code = run_command(f"systemctl status {SERVICE_NAME}", check=False)
    return stdout, stderr, code

def is_service_active():
    """Check if service is active"""
    stdout, stderr, code = run_command(f"systemctl is-active {SERVICE_NAME}", check=False)
    return code == 0

def show_service_logs(lines: int = 50):
    """Show service logs"""
    stdout, stderr, code = run_command(f"journalctl -u {SERVICE_NAME} -n {lines} --no-pager", check=False)
    return stdout

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python3 service_manager.py [install|uninstall|status|logs|start|stop|restart]")
        return 1
    
    command = sys.argv[1]
    
    if not is_systemd_available():
        print("Error: systemd is not available on this system")
        return 1
    
    if command == "install":
        if len(sys.argv) < 7:
            print("Usage: python3 service_manager.py install <timeframe> <symbols> <start_date> <end_date> [capital] [status_filter]")
            return 1
        
        timeframe = sys.argv[2]
        symbols = sys.argv[3]
        start_date = sys.argv[4]
        end_date = sys.argv[5]
        capital = float(sys.argv[6]) if len(sys.argv) > 6 else 10000.0
        status_filter = sys.argv[7] if len(sys.argv) > 7 else "working"
        
        print(f"Installing service for {timeframe} timeframe...")
        
        if create_service_file(timeframe, symbols, start_date, end_date, capital, status_filter):
            if enable_service():
                print("Service installed and started successfully")
                print(f"Logs: journalctl -u {SERVICE_NAME} -f")
            else:
                print("Failed to enable service")
                return 1
        else:
            print("Failed to create service file")
            return 1
    
    elif command == "uninstall":
        print("Uninstalling service...")
        disable_service()
        if remove_service_file():
            run_command("systemctl daemon-reload")
            print("Service uninstalled successfully")
        else:
            print("Failed to remove service file")
            return 1
    
    elif command == "status":
        stdout, stderr, code = get_service_status()
        print(stdout)
        if stderr:
            print(f"Errors: {stderr}")
        print(f"Service is {'active' if is_service_active() else 'inactive'}")
    
    elif command == "logs":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        logs = show_service_logs(lines)
        print(logs)
    
    elif command == "start":
        stdout, stderr, code = run_command(f"systemctl start {SERVICE_NAME}", check=False)
        if code == 0:
            print("Service started")
        else:
            print(f"Failed to start service: {stderr}")
    
    elif command == "stop":
        stdout, stderr, code = run_command(f"systemctl stop {SERVICE_NAME}", check=False)
        if code == 0:
            print("Service stopped")
        else:
            print(f"Failed to stop service: {stderr}")
    
    elif command == "restart":
        stdout, stderr, code = run_command(f"systemctl restart {SERVICE_NAME}", check=False)
        if code == 0:
            print("Service restarted")
        else:
            print(f"Failed to restart service: {stderr}")
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())