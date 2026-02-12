# -*- coding: utf-8 -*-
import os
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Import Config & Logger
try:
    from config_loader import config
    from logger_setup import logger
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from config_loader import config
    from logger_setup import logger

def cleanup_logs(days=7):
    """Delete log files older than X days."""
    log_dir = config.paths.get("logs")
    if not log_dir or not log_dir.exists():
        return

    logger.info(f"Starting Log Cleanup (Age > {days} days)...")
    cutoff = time.time() - (days * 86400)
    
    count = 0
    # Walk through log directory (recursively)
    for root, dirs, files in os.walk(log_dir):
        for file in files:
            if file.endswith(".log") or file.endswith(".log.json"):
                fp = Path(root) / file
                try:
                    mtime = fp.stat().st_mtime
                    if mtime < cutoff:
                        fp.unlink()
                        count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {fp}: {e}")
    
    logger.info(f"Deleted {count} old log files.")

def cleanup_temp_results(days=14):
    """Archive or delete old quicktest results that were not successful."""
    # Logic: If a result is old and not in "Success" listing, it might be trash.
    # For now, let's just clean raw logs in the 'raw' subfolder which accumulate fast.
    
    raw_dir = config.paths.get("logs") / "1h" / "raw"
    if not raw_dir.exists():
        return

    logger.info(f"Starting Raw Log Cleanup (Age > {days} days)...")
    cutoff = time.time() - (days * 86400)
    count = 0
    
    for item in raw_dir.iterdir():
        if item.is_file():
            try:
                if item.stat().st_mtime < cutoff:
                    item.unlink()
                    count += 1
            except:
                pass
                
    logger.info(f"Deleted {count} old raw execution logs.")

def main():
    cleanup_logs(days=7)
    cleanup_temp_results(days=3) # Raw logs are huge, clean them faster

if __name__ == "__main__":
    main()
