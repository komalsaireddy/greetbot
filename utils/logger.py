"""
GreetBot Logger
===============
Centralized structured logging with color-coded terminal output
and file rotation. Use get_logger(__name__) in every module.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── ANSI color codes ─────────────────────────────────────────────────────────

_COLORS = {
    "DEBUG":    "\033[36m",   # Cyan
    "INFO":     "\033[32m",   # Green
    "WARNING":  "\033[33m",   # Yellow
    "ERROR":    "\033[31m",   # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET":    "\033[0m",
    "BOLD":     "\033[1m",
    "DIM":      "\033[2m",
}


class _ColorFormatter(logging.Formatter):
    """Colored formatter for terminal output."""

    FORMAT = (
        "{dim}[{time}]{reset} "
        "{color}{bold}{level:<8}{reset} "
        "{dim}{name}{reset} — {msg}"
    )

    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        reset = _COLORS["RESET"]
        bold = _COLORS["BOLD"]
        dim = _COLORS["DIM"]

        time_str = self.formatTime(record, "%H:%M:%S")

        line = (
            f"{dim}[{time_str}]{reset} "
            f"{color}{bold}{record.levelname:<8}{reset} "
            f"{dim}{record.name}{reset} — "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


class _PlainFormatter(logging.Formatter):
    """Plain formatter for log files."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


# ── Internal cache ────────────────────────────────────────────────────────────

_loggers: dict[str, logging.Logger] = {}
_configured = False


def _configure_root() -> None:
    """Set up handlers on the root logger once."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger("greetbot")
    root.setLevel(logging.DEBUG)
    root.propagate = False

    # ── Console handler ───────────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(_ColorFormatter())
    root.addHandler(console)

    # ── File handler ──────────────────────────────────────────────────────────
    try:
        # Import here to avoid circular import with config
        from config import LOG_FILE, ERROR_LOG

        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,   # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_PlainFormatter())
        root.addHandler(file_handler)

        error_path = Path(ERROR_LOG)
        error_handler = RotatingFileHandler(
            error_path,
            maxBytes=2 * 1024 * 1024,   # 2 MB
            backupCount=2,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(_PlainFormatter())
        root.addHandler(error_handler)

    except Exception:
        pass  # Log files unavailable — console only is fine


def get_logger(name: str) -> logging.Logger:
    """
    Factory for module-level loggers.

    Usage::

        from utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Module ready")

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.

    Returns
    -------
    logging.Logger
        A logger under the ``greetbot`` namespace.
    """
    _configure_root()

    # Namespace under greetbot so the root handlers apply
    full_name = f"greetbot.{name}" if not name.startswith("greetbot") else name

    if full_name not in _loggers:
        logger = logging.getLogger(full_name)
        logger.setLevel(logging.DEBUG)
        _loggers[full_name] = logger

    return _loggers[full_name]
