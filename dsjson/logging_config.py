"""Logging configuration for the dsjson package.

This module provides a centralized logger setup for CLI and library usage.
It writes logs to both console and a file named `conversion.log`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


LOGGER_NAME = "dsjson"
DEFAULT_LOG_FILE_NAME = "conversion.log"


def setup_logger(
    output_dir: str | Path,
    log_level: str = "INFO",
    log_file_name: str = DEFAULT_LOG_FILE_NAME,
    logger_name: str = LOGGER_NAME,
    enable_console: bool = True,
    enable_file: bool = True,
) -> logging.Logger:
    """Configure and return the dsjson logger.

    Parameters
    ----------
    output_dir:
        Directory where the log file should be written.

    log_level:
        Logging level. Supported values are DEBUG, INFO, WARNING, ERROR, CRITICAL.

    log_file_name:
        Name of the log file. Default is conversion.log.

    logger_name:
        Logger name. Default is dsjson.

    enable_console:
        If True, logs are written to console.

    enable_file:
        If True, logs are written to a log file.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(_get_log_level(log_level))

    # Prevent duplicate log messages when setup_logger is called multiple times.
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(_get_log_level(log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if enable_file:
        log_file_path = output_path / log_file_name
        file_handler = logging.FileHandler(
            log_file_path,
            mode="a",
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.debug("Logger initialized")
    logger.debug("Log level: %s", log_level)
    logger.debug("Output directory: %s", output_path.resolve())

    return logger


def get_logger(logger_name: Optional[str] = None) -> logging.Logger:
    """Return an existing dsjson logger.

    This is useful inside modules where logger setup has already happened
    in the CLI or service layer.

    Parameters
    ----------
    logger_name:
        Optional logger name. If not provided, returns the dsjson logger.

    Returns
    -------
    logging.Logger
        Logger instance.
    """
    return logging.getLogger(logger_name or LOGGER_NAME)


def _get_log_level(log_level: str) -> int:
    """Convert a log level string into a logging level constant.

    Parameters
    ----------
    log_level:
        Logging level as string.

    Returns
    -------
    int
        Python logging level.

    Raises
    ------
    ValueError
        If the provided log level is invalid.
    """
    normalized_level = log_level.upper().strip()

    valid_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if normalized_level not in valid_levels:
        raise ValueError(
            f"Invalid log level '{log_level}'. "
            f"Supported levels are: {', '.join(valid_levels)}"
        )

    return valid_levels[normalized_level]