"""Structured JSON logging for the trading system.

Every JSON entry carries the current trading context — timestamp, regime,
probability, equity, positions, daily_pnl — so any line can be understood
in isolation when auditing. The live engine refreshes the context each
cycle via :func:`set_context`.

Files (rotating, 10MB x 30 backups):
    main.log    — everything under the ``regime_trader`` namespace
    trades.log  — executor / order lifecycle events
    regime.log  — HMM and strategy events
    alerts.log  — alert deliveries
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 30

CONTEXT_FIELDS = ("regime", "probability", "equity", "positions", "daily_pnl")

#: Routing of dedicated log files to logger namespaces (all also propagate
#: to main.log through the ``regime_trader`` root).
FILE_ROUTES: dict[str, tuple[str, ...]] = {
    "main.log": ("regime_trader",),
    "trades.log": ("regime_trader.executor", "regime_trader.trades"),
    "regime.log": ("regime_trader.hmm", "regime_trader.strategy",
                   "regime_trader.regime"),
    "alerts.log": ("regime_trader.alerts",),
}

_context: dict[str, Any] = {k: None for k in CONTEXT_FIELDS}


def set_context(**fields: Any) -> None:
    """Update the trading context stamped onto every log entry."""
    for key, value in fields.items():
        if key in CONTEXT_FIELDS:
            _context[key] = value


def get_context() -> dict[str, Any]:
    """Current context (copy)."""
    return dict(_context)


class JsonFormatter(logging.Formatter):
    """Formats records as one JSON object per line with the trading context."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            **_context,
        }
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            entry.update(extra)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def setup_logging(log_dir: str | Path = "logs",
                  level: int = logging.INFO,
                  console: bool = True,
                  max_bytes: int = MAX_BYTES,
                  backup_count: int = BACKUP_COUNT) -> logging.Logger:
    """Configure the regime_trader logging tree (idempotent).

    Args:
        log_dir: Directory for the rotating JSON log files.
        level: Minimum level for the ``regime_trader`` namespace.
        console: Also emit human-readable lines to stderr.
        max_bytes: Rotation size per file (default 10MB).
        backup_count: Rotated files kept per log (default 30).

    Returns:
        The ``regime_trader`` root logger.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    formatter = JsonFormatter()

    # Idempotency: remove handlers this function installed previously.
    for filename, names in FILE_ROUTES.items():
        for name in names:
            logger = logging.getLogger(name)
            for handler in list(logger.handlers):
                if getattr(handler, "_regime_trader_managed", False):
                    logger.removeHandler(handler)
                    handler.close()

    for filename, names in FILE_ROUTES.items():
        handler = RotatingFileHandler(log_path / filename,
                                      maxBytes=max_bytes,
                                      backupCount=backup_count)
        handler.setFormatter(formatter)
        handler._regime_trader_managed = True
        for name in names:
            logging.getLogger(name).addHandler(handler)

    root = logging.getLogger("regime_trader")
    root.setLevel(level)
    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter(
            "%(levelname)s %(name)s: %(message)s"))
        stream._regime_trader_managed = True
        root.addHandler(stream)
    root.debug("logging configured (dir=%s)", log_path)
    return root


def get_logger(component: str) -> logging.Logger:
    """Logger for a component under the regime_trader namespace."""
    return logging.getLogger(f"regime_trader.{component}")
