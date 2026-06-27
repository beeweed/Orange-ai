"""Structured logging utility.

Provides a single configured logger factory so every module emits consistent,
timestamped, level-tagged logs suitable for production observability.
"""
from __future__ import annotations

import logging
import sys
from functools import lru_cache

from src.config.settings import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    settings = get_settings()
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False
    return logger
