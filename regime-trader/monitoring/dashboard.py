"""Terminal-based live dashboard built on rich.

Sectioned layout: REGIME / PORTFOLIO / POSITIONS / RECENT SIGNALS /
RISK STATUS / SYSTEM, with color-coded drawdown bars. Two modes:
- In-process: TradingSystem calls ``update(snapshot)`` each cycle.
- Detached: ``Dashboard.watch(path)`` tails state_snapshot.json written by a
  running instance (the ``--dashboard`` CLI flag).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

BAR_WIDTH = 14


def _fmt(value: Any, fmt: str, fallback: str = "n/a") -> str:
    try:
        return fmt.format(value)
    except (TypeError, ValueError):
        return fallback


def _risk_bar(value: float | None, limit: float | None) -> str:
    """Color-coded utilization bar: green < 50%, yellow < 80%, red beyond."""
    if value is None or not limit:
        return "n/a"
    ratio = max(0.0, min(1.0, value / limit))
    filled = round(ratio * BAR_WIDTH)
    color = "green" if ratio < 0.5 else "yellow" if ratio < 0.8 else "red"
    icon = "✅" if ratio < 0.8 else "⚠️" if ratio < 1.0 else "⛔"
    return (f"[{color}]{'█' * filled}{'░' * (BAR_WIDTH - filled)}[/] "
            f"{value:.1%}/{limit:.0%} {icon}")


def _holding(days: float | None) -> str:
    if days is None:
        return "-"
    return f"{days * 24:.0f}h" if days < 1 else f"{days:.1f}d"


class Dashboard:
    """Compact terminal dashboard over the system's state snapshot.

    Args:
        refresh_seconds: Minimum seconds between renders (throttle).
        console: Injectable rich console for tests.
    """

    def __init__(self, refresh_seconds: int = 5,
                 console: Console | None = None) -> None:
        self.refresh_seconds = refresh_seconds
        self.console = console or Console()
        self._last_render = 0.0

    def start(self) -> None:
        """No-op (rendering happens on update)."""

    def stop(self) -> None:
        """No-op (rendering happens on update)."""

    def update(self, snapshot: dict[str, Any], force: bool = False) -> None:
        """Render the snapshot unless the throttle window hasn't elapsed."""
        now = time.monotonic()
        if not force and now - self._last_render < self.refresh_seconds:
            return
        self._last_render = now
        self.console.print(self._render(snapshot))

    # -------------------------------------------------------------- render

    def _render(self, snap: dict[str, Any]) -> Panel:
        sections = [
            self._section("REGIME", self._regime_lines(snap)),
            self._section("PORTFOLIO", self._portfolio_lines(snap)),
        ]
        if snap.get("positions"):
            sections.append(self._section("POSITIONS",
                                          self._position_lines(snap)))
        if snap.get("last_signals"):
            sections.append(self._section("RECENT SIGNALS",
                                          self._signal_lines(snap)))
        sections.append(self._section("RISK STATUS", self._risk_lines(snap)))
        sections.append(self._section("SYSTEM", self._system_lines(snap)))
        return Panel(Group(*sections),
                     title=f"regime-trader — {snap.get('timestamp', '')}",
                     border_style="cyan")

    @staticmethod
    def _section(title: str, lines: list[str]) -> Panel:
        return Panel(Group(*(Text.from_markup(line) for line in lines)),
                     title=title, title_align="left", border_style="dim")

    @staticmethod
    def _regime_lines(snap: dict[str, Any]) -> list[str]:
        regime = str(snap.get("regime") or "n/a").upper()
        conf = snap.get("regime_confidence")
        stability = snap.get("regime_stability")
        flicker = snap.get("flicker_rate")
        window = snap.get("flicker_window")
        confirmed = snap.get("regime_confirmed")
        parts = [f"[bold]{regime}[/]"
                 + (f" ({conf:.0%})" if conf is not None else "")]
        if stability is not None:
            parts.append(f"Stability: {stability} bars")
        if flicker is not None and window:
            parts.append(f"Flicker: {flicker:.0f}/{window}")
        if confirmed is False:
            parts.append("[yellow]UNCONFIRMED[/]")
        return [" | ".join(parts)]

    @staticmethod
    def _portfolio_lines(snap: dict[str, Any]) -> list[str]:
        equity = snap.get("equity")
        pnl = snap.get("daily_pnl")
        pnl_pct = snap.get("daily_pnl_pct")
        daily = "n/a"
        if pnl is not None:
            color = "green" if pnl >= 0 else "red"
            daily = f"[{color}]{pnl:+,.0f}"
            if pnl_pct is not None:
                daily += f" ({pnl_pct:+.2%})"
            daily += "[/]"
        line1 = (f"Equity: {_fmt(equity, '${:,.0f}')} | Daily: {daily}")
        line2 = (f"Allocation: {_fmt(snap.get('allocation'), '{:.0%}')} | "
                 f"Leverage: {_fmt(snap.get('leverage'), '{:.2f}x')}")
        return [line1, line2]

    @staticmethod
    def _position_lines(snap: dict[str, Any]) -> list[str]:
        lines = []
        for sym, p in (snap.get("positions") or {}).items():
            pnl_pct = p.get("pnl_pct")
            color = "green" if (pnl_pct or 0) >= 0 else "red"
            lines.append(
                f"{sym} | LONG | {_fmt(p.get('current_price'), '${:,.2f}')} | "
                f"[{color}]{_fmt(pnl_pct, '{:+.1%}')}[/] | "
                f"Stop: {_fmt(p.get('stop'), '${:,.2f}', '-')} | "
                f"{_holding(p.get('holding_days'))}")
        return lines

    @staticmethod
    def _signal_lines(snap: dict[str, Any]) -> list[str]:
        lines = []
        for s in (snap.get("last_signals") or [])[-6:]:
            if s.get("approved"):
                detail = (f"[green]{s.get('strategy', '')} "
                          f"x{s.get('qty', '')}[/]")
                notes = "; ".join(s.get("modifications") or [])
                if notes:
                    detail += f" [dim]({notes})[/]"
            else:
                detail = f"[red]rejected: {s.get('reason', '')}[/]"
            lines.append(f"{s.get('time', '')} | {s.get('symbol', '')} | "
                         f"{detail}")
        return lines

    @staticmethod
    def _risk_lines(snap: dict[str, Any]) -> list[str]:
        breaker = str(snap.get("breaker_status") or "n/a")
        breaker_color = {"normal": "green", "reduced": "yellow"}.get(
            breaker, "red")
        return [
            f"Daily DD:  {_risk_bar(snap.get('daily_dd'), snap.get('daily_dd_limit'))}",
            f"From Peak: {_risk_bar(snap.get('peak_dd'), snap.get('peak_dd_limit'))}",
            f"Breaker: [{breaker_color}]{breaker.upper()}[/] | "
            f"Trades today: {snap.get('trades_today', 0)}",
        ]

    @staticmethod
    def _system_lines(snap: dict[str, Any]) -> list[str]:
        feed = "✅" if snap.get("feed_ok", True) else "[red]❌ STALE[/]"
        api = "✅" if snap.get("api_ok", True) else "[red]❌[/]"
        latency = snap.get("api_latency_ms")
        if latency is not None and snap.get("api_ok", True):
            api += f" {latency:.0f}ms"
        age = snap.get("model_age_days")
        model = f"{age:.0f}d ago" if age is not None else "n/a"
        mode = str(snap.get("mode") or
                   ("DRY RUN" if snap.get("dry_run") else "PAPER"))
        mode_color = {"PAPER": "cyan", "DRY RUN": "yellow"}.get(mode, "red")
        line = (f"Data: {feed} | API: {api} | HMM: {model} | "
                f"[{mode_color}]{mode}[/]")
        if snap.get("error"):
            line += f"\n[red]Last error: {snap['error']}[/]"
        return [line]

    # -------------------------------------------------------------- attach

    @classmethod
    def watch(cls, snapshot_path: str | Path,
              refresh_seconds: int = 5) -> None:
        """Tail a running instance's state_snapshot.json (Ctrl-C to exit)."""
        path = Path(snapshot_path)
        dash = cls(refresh_seconds=refresh_seconds)
        last_stamp = None
        dash.console.print(f"watching {path} — Ctrl-C to exit")
        try:
            while True:
                if path.exists():
                    try:
                        snap = json.loads(path.read_text())
                    except (OSError, json.JSONDecodeError):
                        snap = None  # mid-write; retry next tick
                    if snap and snap.get("timestamp") != last_stamp:
                        last_stamp = snap.get("timestamp")
                        dash.update(snap, force=True)
                else:
                    dash.console.print(f"waiting for {path} "
                                       "(is the system running?)")
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            dash.console.print("dashboard detached")
