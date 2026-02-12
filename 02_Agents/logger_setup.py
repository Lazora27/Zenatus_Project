# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

# Handle relative import when running as module or script
try:
    from .config_loader import config
except ImportError:
    from config_loader import config

def setup_logger(name="zenatus"):
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
        
    log_level_str = config.get("logging", "level", "INFO")
    logger.setLevel(getattr(logging, log_level_str.upper()))

    # JSON Formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d'
    )

    # Console Handler (JSON)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler with Rotation
    try:
        log_dir = config.paths.get("logs")
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = config.get("logging", "file_name", "pipeline.log")
            
            # Rotate after 10MB, keep 5 backups
            file_handler = RotatingFileHandler(
                log_dir / log_file, 
                maxBytes=10*1024*1024, 
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    return logger

# Global logger instance
logger = setup_logger()
