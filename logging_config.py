import logging
import os
from logging.handlers import RotatingFileHandler

# Import configuration
try:
    from config import LOG_DIR, LOG_LEVEL
    DEFAULT_LOG_DIR = LOG_DIR
    DEFAULT_LOG_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)
except ImportError:
    DEFAULT_LOG_DIR = '/var/log/molt-server'
    DEFAULT_LOG_LEVEL = logging.INFO

def setup_logging(log_dir=None, level=None):
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
    if level is None:
        level = DEFAULT_LOG_LEVEL
    """Setup structured logging with rotation."""
    # Create log directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('molt_server')
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        f'{log_dir}/molt-server.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
