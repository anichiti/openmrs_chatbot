import logging
import logging.handlers
import sys
import io
from utils.config import LOG_LEVEL, LOG_FILE

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # Suppress verbose libraries
    logging.getLogger("chromadb").setLevel(logging.ERROR)
    logging.getLogger("langchain").setLevel(logging.ERROR)
    logging.getLogger("langchain_core").setLevel(logging.ERROR)
    logging.getLogger("langchain_community").setLevel(logging.ERROR)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=10485760, backupCount=5, encoding='utf-8'
    )
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Force UTF-8 encoding on console handler for Windows compatibility
    if sys.platform == 'win32':
        console_handler.stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    formatter = logging.Formatter(
        '%(message)s'  # Simpler format for console - only show the message
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'  # Detailed format for file
    )
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
