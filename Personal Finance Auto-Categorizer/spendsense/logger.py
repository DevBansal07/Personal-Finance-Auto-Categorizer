"""
Centralized logging configuration for SpendSense.

Provides a consistent log format and a factory function
for module-level loggers across the application.
"""

import io
import logging
import sys

# ── Format ──────────────────────────────────────────────────────────
LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def setup_logging(level: int = logging.INFO) -> None:
    """Initialize the root logger with console output.

    Safe to call multiple times — only configures handlers once.

    Args:
        level: Logging level (default: INFO).
    """
    global _initialized
    if _initialized:
        return

    root_logger = logging.getLogger("spendsense")
    root_logger.setLevel(level)

    # Console handler — force UTF-8 encoding for Windows compatibility
    utf8_stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console_handler = logging.StreamHandler(utf8_stream)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root_logger.addHandler(console_handler)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the 'spendsense' hierarchy.

    Args:
        name: Module name (e.g., 'data_loader', 'categorizer').

    Returns:
        A configured logging.Logger instance.
    """
    return logging.getLogger(f"spendsense.{name}")
