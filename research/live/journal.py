"""Append-only journal: every decision, order, and fill, with a reason.

One JSON object per line. Nothing is ever rewritten or deleted. If you cannot
explain a position from this file alone, the journal has failed.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import JOURNAL_PATH


def _write(record: dict, path: Path = None):
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              **record}
    with open(path or JOURNAL_PATH, "a") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    return record


def decision(as_of, symbol, target_w, current_w, reason, **extra):
    return _write({"kind": "decision", "as_of": str(as_of), "symbol": symbol,
                   "target_weight": round(float(target_w), 6),
                   "current_weight": round(float(current_w), 6),
                   "reason": reason, **extra})


def order(as_of, symbol, side, qty, notional, reason, order_id=None, **extra):
    return _write({"kind": "order", "as_of": str(as_of), "symbol": symbol,
                   "side": side, "qty": float(qty),
                   "notional": round(float(notional), 2), "reason": reason,
                   "order_id": order_id, **extra})


def fill(as_of, symbol, side, qty, price, order_id=None, **extra):
    return _write({"kind": "fill", "as_of": str(as_of), "symbol": symbol,
                   "side": side, "qty": float(qty), "price": float(price),
                   "order_id": order_id, **extra})


def rejected(as_of, symbol, reason, **extra):
    """An order the limits layer refused. These matter as much as fills."""
    return _write({"kind": "rejected", "as_of": str(as_of), "symbol": symbol,
                   "reason": reason, **extra})


def event(as_of, what, detail=None, severity="info"):
    return _write({"kind": "event", "as_of": str(as_of), "what": what,
                   "severity": severity, "detail": detail or {}})


def snapshot(as_of, equity, positions, gross, halted, **extra):
    return _write({"kind": "snapshot", "as_of": str(as_of),
                   "equity": round(float(equity), 2), "positions": positions,
                   "gross_exposure": round(float(gross), 4),
                   "halted": bool(halted), **extra})


def read_all(path: Path = None):
    p = Path(path or JOURNAL_PATH)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
