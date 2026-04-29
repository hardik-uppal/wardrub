"""Logging configuration for the Wardrub backend."""

import logging
import sys
from datetime import datetime
from pathlib import Path
import json
from typing import Any

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file path with date
LOG_FILE = LOGS_DIR / f"wardrub_{datetime.now().strftime('%Y-%m-%d')}.log"


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easier parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data
            
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console output for better readability."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format: [TIME] LEVEL | MODULE.FUNCTION:LINE | MESSAGE
        timestamp = datetime.now().strftime("%H:%M:%S")
        level = f"{color}{record.levelname:8}{self.RESET}"
        location = f"{record.module}.{record.funcName}:{record.lineno}"
        
        formatted = f"[{timestamp}] {level} | {location:40} | {record.getMessage()}"
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
            
        return formatted


def setup_logging(level: str = "DEBUG") -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Root logger instance
    """
    # Get root logger
    logger = logging.getLogger("wardrub")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler with JSON
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Also capture uvicorn logs
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = logger.handlers
    
    logger.info(f"📝 Logging initialized. Log file: {LOG_FILE}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"wardrub.{name}")
    return logging.getLogger("wardrub")


class LogContext:
    """Context manager for logging with extra data."""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"🚀 Starting: {self.operation}", extra={"extra_data": self.extra})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"❌ Failed: {self.operation} ({duration:.2f}s)",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={"extra_data": {**self.extra, "duration_seconds": duration}}
            )
        else:
            self.logger.info(
                f"✅ Completed: {self.operation} ({duration:.2f}s)",
                extra={"extra_data": {**self.extra, "duration_seconds": duration}}
            )
        
        return False  # Don't suppress exceptions





