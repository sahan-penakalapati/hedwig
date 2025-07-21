"""
Centralized logging configuration for the Hedwig system.

Provides structured logging across all components with configurable
log levels and output formatting.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


class HedwigLogger:
    """Centralized logging configuration for Hedwig."""
    
    _configured = False
    
    @classmethod
    def configure(
        cls,
        log_level: str = "INFO",
        log_dir: Optional[Path] = None,
        console_output: bool = True,
        file_output: bool = True
    ) -> None:
        """
        Configure logging for the Hedwig application.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (defaults to ~/.hedwig/logs)
            console_output: Whether to output logs to console
            file_output: Whether to output logs to file
        """
        if cls._configured:
            return
        
        # Set up log directory
        if log_dir is None:
            log_dir = Path.home() / '.hedwig' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if file_output:
            log_file = log_dir / 'hedwig.log'
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Always capture debug in files
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Set up specific logger levels for external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.INFO)
        logging.getLogger('langchain').setLevel(logging.INFO)
        
        cls._configured = True
        
        # Log configuration info
        logger = logging.getLogger(__name__)
        logger.info(f"Hedwig logging configured - Level: {log_level}, Console: {console_output}, File: {file_output}")
        if file_output:
            logger.info(f"Log files location: {log_dir}")
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a logger instance for a specific component.
        
        Args:
            name: Name for the logger (typically __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)
    
    @classmethod
    def configure_from_env(cls) -> None:
        """Configure logging from environment variables."""
        log_level = os.getenv('HEDWIG_LOG_LEVEL', 'INFO')
        log_dir_str = os.getenv('HEDWIG_LOG_DIR')
        log_dir = Path(log_dir_str) if log_dir_str else None
        
        console_output = os.getenv('HEDWIG_CONSOLE_LOGGING', 'true').lower() == 'true'
        file_output = os.getenv('HEDWIG_FILE_LOGGING', 'true').lower() == 'true'
        
        cls.configure(
            log_level=log_level,
            log_dir=log_dir,
            console_output=console_output,
            file_output=file_output
        )


def setup_logging(log_level: str = "INFO") -> None:
    """
    Quick setup function for basic logging configuration.
    
    Args:
        log_level: Logging level
    """
    HedwigLogger.configure(log_level=log_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return HedwigLogger.get_logger(name)