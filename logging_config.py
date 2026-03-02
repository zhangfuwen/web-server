import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir='/var/log/molt-server', level=logging.INFO):
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
