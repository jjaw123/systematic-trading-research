"""Alerts for critical events: console, log file, email, webhook.

Triggers: regime change, circuit breaker, large P&L swings, data feed down,
API lost, HMM retrained, flicker exceeded (plus order rejections and system
errors). Alerts of the same kind are rate-limited (default 1 per 15 min);
CRITICAL alerts always go out.
"""

from __future__ import annotations

import json
import logging
import smtplib
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from enum import Enum
from typing import Any

logger = logging.getLogger("regime_trader.alerts")


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertKind(Enum):
    """Alert categories used for rate-limiting and routing."""

    REGIME_CHANGE = "regime_change"
    CIRCUIT_BREAKER = "circuit_breaker"
    LARGE_PNL = "large_pnl"
    DATA_FEED_DOWN = "data_feed_down"
    API_LOST = "api_lost"
    HMM_RETRAINED = "hmm_retrained"
    FLICKER_EXCEEDED = "flicker_exceeded"
    ORDER_REJECTED = "order_rejected"
    SYSTEM_ERROR = "system_error"


@dataclass(frozen=True)
class Alert:
    """One dispatched alert (kept in history)."""

    timestamp: datetime
    kind: AlertKind
    level: AlertLevel
    message: str
    context: dict[str, Any] = field(default_factory=dict)


_LOG_LEVELS = {AlertLevel.INFO: logging.INFO,
               AlertLevel.WARNING: logging.WARNING,
               AlertLevel.CRITICAL: logging.CRITICAL}


class AlertManager:
    """Dispatches rate-limited alerts to the configured channels.

    Args:
        rate_limit_minutes: Min minutes between alerts of the same kind
            (CRITICAL bypasses the limit).
        email_config: SMTP settings {host, port, from, to, username?,
            password?, use_tls?}; None disables email.
        webhook_url: POST target for JSON alert payloads; None disables.
        console: Also print alerts to the terminal.
        now: Injectable clock for tests.
    """

    def __init__(self,
                 rate_limit_minutes: float = 15,
                 email_config: dict[str, Any] | None = None,
                 webhook_url: str | None = None,
                 console: bool = True,
                 now: Callable[[], datetime] | None = None) -> None:
        self.rate_limit_minutes = rate_limit_minutes
        self.email_config = email_config
        self.webhook_url = webhook_url
        self.console = console
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._last_sent: dict[AlertKind, datetime] = {}
        self._history: list[Alert] = []

    def send(self, kind: AlertKind, level: AlertLevel, message: str,
             **context: Any) -> bool:
        """Dispatch an alert unless rate-limited.

        Returns:
            True if dispatched, False if suppressed by the rate limit.
        """
        now = self._now()
        if level is not AlertLevel.CRITICAL and self._rate_limited(kind, now):
            logger.debug("alert suppressed (rate limit): %s %s",
                         kind.value, message)
            return False
        self._last_sent[kind] = now
        alert = Alert(now, kind, level, message, context)
        self._history.append(alert)

        logger.log(_LOG_LEVELS[level], "ALERT [%s] %s", kind.value, message,
                   extra={"context": {"alert_kind": kind.value,
                                      "alert_level": level.value, **context}})
        if self.console:
            self._print(alert)
        if self.email_config:
            self._safely(self._send_email, alert)
        if self.webhook_url:
            self._safely(self._send_webhook, alert)
        return True

    def get_history(self, limit: int | None = None) -> list[Alert]:
        return self._history[-limit:] if limit else list(self._history)

    # ------------------------------------------------------------- internals

    def _rate_limited(self, kind: AlertKind, now: datetime) -> bool:
        last = self._last_sent.get(kind)
        if last is None:
            return False
        return (now - last).total_seconds() < self.rate_limit_minutes * 60

    def _print(self, alert: Alert) -> None:
        try:
            from rich.console import Console
            colors = {AlertLevel.INFO: "cyan", AlertLevel.WARNING: "yellow",
                      AlertLevel.CRITICAL: "bold red"}
            Console(stderr=True).print(
                f"[{colors[alert.level]}]🔔 {alert.level.value.upper()} "
                f"[{alert.kind.value}] {alert.message}[/]")
        except Exception:
            print(f"ALERT {alert.level.value} [{alert.kind.value}] "
                  f"{alert.message}")

    def _safely(self, sender: Callable[[Alert], None], alert: Alert) -> None:
        try:
            sender(alert)
        except Exception:
            logger.exception("alert delivery failed via %s", sender.__name__)

    def _send_email(self, alert: Alert) -> None:
        cfg = self.email_config or {}
        msg = EmailMessage()
        msg["Subject"] = (f"[regime-trader] {alert.level.value.upper()}: "
                          f"{alert.kind.value}")
        msg["From"] = cfg["from"]
        msg["To"] = cfg["to"]
        body = alert.message
        if alert.context:
            body += "\n\n" + json.dumps(alert.context, indent=2, default=str)
        msg.set_content(body)
        with smtplib.SMTP(cfg["host"], int(cfg.get("port", 587)),
                          timeout=10) as smtp:
            if cfg.get("use_tls", True):
                smtp.starttls()
            if cfg.get("username"):
                smtp.login(cfg["username"], cfg.get("password", ""))
            smtp.send_message(msg)

    def _send_webhook(self, alert: Alert) -> None:
        payload = json.dumps({
            "timestamp": alert.timestamp.isoformat(),
            "kind": alert.kind.value,
            "level": alert.level.value,
            "message": alert.message,
            "context": alert.context,
        }, default=str).encode()
        request = urllib.request.Request(
            self.webhook_url, data=payload,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(request, timeout=10).read()
