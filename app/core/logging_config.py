"""
Logging configuration.

Sets up a simple, consistent logger for the application.
"""

import logging
import os


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("health_genai")
    logger.setLevel(level)
    return logger


logger = setup_logging()
