"""Logging utilities for the AI employee system."""

import logging
import sys
from pathlib import Path
from typing import Optional

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Set up root logging for the application.

    Args:
        log_level: One of DEBUG / INFO / WARNING / ERROR / CRITICAL.
        log_file:  Optional path to a log file (directory is created if absent).

    Returns:
        Configured root logger.

    Raises:
        ValueError: If log_level is not a valid level name.
    """
    level_upper = log_level.upper()
    if level_upper not in _VALID_LEVELS:
        raise ValueError(
            f"Invalid log level '{log_level}'. Must be one of: {', '.join(sorted(_VALID_LEVELS))}"
        )
    numeric_level = getattr(logging, level_upper)

    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Remove any handlers added by earlier calls so this is idempotent.
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_path = Path(log_file)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as exc:
            logger.warning(f"Could not create log file handler at '{file_path}': {exc}")

    return logger
