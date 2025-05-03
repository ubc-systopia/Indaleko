#!/usr/bin/env python3
"""
Logging utilities for the enhanced data generator.
"""

import logging
import os
import sys
from datetime import datetime


def setup_logging(level=logging.INFO, log_file=None):
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file. If None, logs will only go to console.
    """
    # Create logs directory if it doesn't exist
    if log_file is None:
        os.makedirs('logs', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"logs/data_generator_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler if log_file is provided
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress excessive logging from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name, level=None):
    """
    Get a logger with the specified name and optional level.
    
    Args:
        name: Logger name, typically __name__
        level: Optional logging level to override the root logger's level
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger