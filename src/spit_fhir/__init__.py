import logging
import logging.config
import os
import sys
from pathlib import Path

try:
    from rich.logging import RichHandler  # noqa: F401

    IS_RICH = True
except ImportError:
    IS_RICH = False

__version__ = "0.0.1"


def is_interactive() -> bool:
    if hasattr(sys, "ps1"):  # ps1 should be present for interactive shells
        return True
    return os.isatty(sys.stdin.fileno())


def setup_logging(level: str = "INFO", log_file: str | None = "output/log.txt") -> None:
    """Configure root logging. Uses Rich's handler when available and running
    in an interactive terminal; otherwise a plain formatted stream handler.

    Log messages are streamed to the console and, unless log_file is None,
    also written to file.
    """
    use_rich = is_interactive() and IS_RICH

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "rich": {"datefmt": "%H:%M:%S"},
            "detailed": {"format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
    }
    if use_rich:
        config["handlers"]["console"]["class"] = "rich.logging.RichHandler"
        config["handlers"]["console"]["formatter"] = "rich"
        config["handlers"]["console"]["rich_tracebacks"] = True
        config["handlers"]["console"]["markup"] = True

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "filename": log_file,
            "formatter": "detailed",
            "level": level,
        }
        config["root"]["handlers"].append("file")

    logging.config.dictConfig(config)
