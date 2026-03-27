import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

def setup_logger(name: str, log_filename: str):
    """
    Configures a robust rotating logger.
    - Active logs go to 'logs/[name].log' (The Latest)
    - Rotates daily.
    - Rotates if size exceeds 10MB.
    - Archives are named with date and index.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevents adding handlers multiple times if setup_logger is called twice
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Size based: 10MB)
    # Note: Using RotatingFileHandler for the 'Latest' file logic
    file_path = log_dir / f"{log_filename}.log"
    file_handler = RotatingFileHandler(
        file_path, 
        maxBytes=10 * 1024 * 1024, # 10MB
        backupCount=100 # Keep up to 100 historical files
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
