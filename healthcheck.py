#!/usr/bin/env python3
import sys
import psutil
import os
import time

def check_process_running(process_name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and process_name in ' '.join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def check_log_activity(log_path, max_age_seconds=300):
    if not os.path.exists(log_path):
        return False
    
    mtime = os.path.getmtime(log_path)
    age = time.time() - mtime
    return age < max_age_seconds

def main():
    # 1. Check if Orchestrator is running
    if not check_process_running("pipeline_orchestrator.py"):
        print("Orchestrator not running")
        sys.exit(1)
        
    # 2. Check if logs are being written (activity check)
    # This might be tricky if the system is idle (waiting for new strategies)
    # So maybe only warn or skip this check if "idle" mode is active.
    
    # For now, just process check is good enough for basic health
    sys.exit(0)

if __name__ == "__main__":
    main()
