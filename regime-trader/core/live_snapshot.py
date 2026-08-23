"""State-snapshot assembly for the live engine.

Builds the dict that serves three consumers: the crash-recovery file
(state_snapshot.json), the in-process dashboard, and the detached
``--dashboard`` viewer. Every field is best-effort — a failing component
yields None rather than breaking the snapshot.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("regime_trader.live")


def model_age_days(engine: Any) -> float | None:
    """Days since the engine was trained, from its metadata."""
    trained = engine.metadata.get("training_date") if engine else None
    if not trained:
        return None
    age = datetime.now(timezone.utc) - datetime.fromisoformat(trained)
    return age.total_seconds() / 86_400


def save_snapshot(path: Path, snap: dict[str, Any]) -> None:
    """Atomically persist the snapshot (write to .tmp, then rename).

    Also appends a slim record to the rolling history file next to it, which
    is what the dashboard's equity curve and regime ribbon read. History is
    best-effort and never blocks the snapshot itself.
    """
    try:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(snap, indent=2, default=str))
        tmp.replace(path)
    except Exception:
        logger.exception("snapshot save failed")
    try:
        from monitoring import history

        history.append(history.history_path(path.parent), snap)
    except Exception:
        logger.debug("history append skipped", exc_info=True)


def restore_snapshot(system: Any) -> None:
    """Restore same-day counters and stop levels from a prior session."""
    path = system.snapshot_path
    if not path.exists():
        return
    try:
        snap = json.loads(path.read_text())
    except Exception:
        logger.exception("snapshot unreadable — starting fresh")
        return
    logger.info("recovering session state from %s (saved %s)",
                path, snap.get("timestamp"))
    if snap.get("date") == datetime.now(timezone.utc).date().isoformat():
        system.tracker.trades_today = int(snap.get("trades_today") or 0)
        if snap.get("day_start_equity"):
            system.tracker.day_start_equity = float(snap["day_start_equity"])
        if snap.get("week_start_equity"):
            system.tracker.week_start_equity = float(snap["week_start_equity"])
    for symbol, pos in (snap.get("positions") or {}).items():
        if pos.get("stop") and symbol in system.tracker.positions:
            system.tracker.set_stop(symbol, float(pos["stop"]))


def build_snapshot(system: Any, error: str | None = None) -> dict[str, Any]:
    """Assemble the full state snapshot from a TradingSystem instance."""
    now = datetime.now(timezone.utc)
    equity: float | None = None
    api_ok, api_latency_ms = True, None
    try:
        t0 = time.perf_counter()
        account = system.client.get_account()
        api_latency_ms = (time.perf_counter() - t0) * 1000
        equity = float(account.get("equity") or 0.0)
    except Exception:
        api_ok = False

    tracker = system.tracker
    positions: dict[str, dict[str, Any]] = {}
    gross_value = 0.0
    if tracker is not None:
        for sym, p in tracker.positions.items():
            positions[sym] = {
                "qty": p.qty,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "stop": p.stop_level,
                "unrealized_pnl": p.unrealized_pnl,
                "pnl_pct": (p.current_price / p.entry_price - 1)
                if p.entry_price > 0 else None,
                "holding_days": p.holding_days,
                "regime_at_entry": p.regime_at_entry,
            }
            gross_value += abs(p.market_value)

    allocation = gross_value / equity if equity else None
    day_start = tracker.day_start_equity if tracker else None
    week_start = tracker.week_start_equity if tracker else None
    daily_pnl = daily_pnl_pct = daily_dd = None
    if equity is not None and day_start:
        daily_pnl = equity - day_start
        daily_pnl_pct = daily_pnl / day_start
        daily_dd = max(0.0, -daily_pnl_pct)
    peak = tracker.peak_equity if tracker else None
    peak_dd = (max(0.0, 1.0 - equity / peak)
               if equity is not None and peak else None)

    regime_stability = flicker_rate = None
    engine = system.engine
    if engine is not None:
        try:
            regime_stability = engine.get_regime_stability()
            flicker_rate = engine.get_regime_flicker_rate()
        except Exception:
            pass

    risk_cfg = system.risk_manager.config if system.risk_manager else None
    state = system.regime_state
    mode = ("DRY RUN" if system.dry_run
            else "PAPER" if getattr(system.client, "paper", True) else "LIVE")

    return {
        "timestamp": now.isoformat(),
        "date": now.date().isoformat(),
        "dry_run": system.dry_run,
        "mode": mode,
        "equity": equity,
        "session_start_equity": system.session_start_equity,
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": daily_pnl_pct,
        "allocation": allocation,
        "leverage": max(1.0, allocation) if allocation is not None else None,
        "regime": state.label.value if state else None,
        "regime_confidence": state.probability if state else None,
        "regime_confirmed": state.is_confirmed if state else None,
        "regime_stability": regime_stability,
        "flicker_rate": flicker_rate,
        "flicker_window": engine.flicker_window if engine else None,
        "breaker_status": system.risk_manager.breaker.status.value
        if system.risk_manager else None,
        "daily_dd": daily_dd,
        "daily_dd_limit": risk_cfg.daily_dd_halt if risk_cfg else None,
        "peak_dd": peak_dd,
        "peak_dd_limit": risk_cfg.max_dd_from_peak if risk_cfg else None,
        "trades_today": tracker.trades_today if tracker else 0,
        "day_start_equity": day_start,
        "week_start_equity": week_start,
        "positions": positions,
        "last_signals": list(system._last_signals),
        "feed_ok": system.feed_ok(),
        "api_ok": api_ok,
        "api_latency_ms": api_latency_ms,
        "model_age_days": model_age_days(engine),
        "error": error,
    }
