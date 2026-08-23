"""Rolling history of state snapshots, for the dashboard's time-series views.

The live engine writes one *slim* record per cycle to ``state_history.jsonl``
(append-only, one JSON object per line) alongside the full
``state_snapshot.json``. The snapshot answers "what is true now"; this file
answers "how did we get here" — the equity curve, the regime ribbon and the
drawdown trend all read from it.

Every function is best-effort: a corrupt line is skipped, an unreadable file
yields an empty frame. History is a convenience, never a dependency — the
trading loop must not fail because a chart is unavailable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger("regime_trader.monitoring")

HISTORY_FILENAME = "state_history.jsonl"

#: Fields carried forward from the full snapshot. Kept deliberately narrow —
#: positions and signals are point-in-time and belong in the snapshot only.
FIELDS: tuple[str, ...] = (
    "timestamp", "equity", "daily_pnl", "daily_pnl_pct", "allocation",
    "leverage", "regime", "regime_confidence", "regime_confirmed",
    "daily_dd", "peak_dd", "trades_today", "breaker_status", "mode",
    "api_latency_ms",
)

NUMERIC: tuple[str, ...] = (
    "equity", "daily_pnl", "daily_pnl_pct", "allocation", "leverage",
    "regime_confidence", "daily_dd", "peak_dd", "trades_today",
    "api_latency_ms",
)

#: Trim to this many records once the file grows past ``TRIM_AT_BYTES``.
MAX_RECORDS = 4000
TRIM_AT_BYTES = 2_000_000


def history_path(root: Path) -> Path:
    """Location of the history file for a project root."""
    return Path(root) / HISTORY_FILENAME


def slim(snap: dict[str, Any]) -> dict[str, Any]:
    """Project a full snapshot down to the fields worth keeping over time."""
    return {key: snap.get(key) for key in FIELDS}


def append(path: Path, snap: dict[str, Any]) -> None:
    """Append one record. Never raises — history is best-effort."""
    try:
        record = slim(snap)
        if not record.get("timestamp"):
            return
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        _trim_if_large(Path(path))
    except Exception:
        logger.debug("history append failed", exc_info=True)


def _trim_if_large(path: Path) -> None:
    """Keep the newest ``MAX_RECORDS`` lines once the file gets big.

    Rewrites via a temp file and an atomic rename so a reader never observes
    a half-written history.
    """
    try:
        if path.stat().st_size < TRIM_AT_BYTES:
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= MAX_RECORDS:
            return
        tmp = path.with_suffix(".jsonl.tmp")
        tmp.write_text("\n".join(lines[-MAX_RECORDS:]) + "\n", encoding="utf-8")
        tmp.replace(path)
    except Exception:
        logger.debug("history trim failed", exc_info=True)


def load(path: Path, limit: int = 1500) -> pd.DataFrame:
    """Read the newest ``limit`` records into a typed, time-sorted frame.

    Returns an empty frame with the expected columns when the file is absent,
    empty or unreadable, so callers can branch on ``.empty`` alone.
    """
    empty = pd.DataFrame(columns=list(FIELDS))
    path = Path(path)
    if not path.exists():
        return empty
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return empty

    records = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue          # mid-write or truncated tail — skip it
        if isinstance(parsed, dict):
            records.append(parsed)
    if not records:
        return empty

    frame = pd.DataFrame(records).reindex(columns=list(FIELDS))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce",
                                        utc=True, format="mixed")
    frame = frame.dropna(subset=["timestamp"])
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("timestamp").reset_index(drop=True)


def regime_runs(frame: pd.DataFrame) -> list[tuple[str, int]]:
    """Collapse the regime column into ``(label, run_length)`` pairs.

    Feeds the regime ribbon: consecutive identical labels become one segment,
    so a 400-row history renders as a handful of spans rather than 400.
    """
    if frame.empty or "regime" not in frame:
        return []
    runs: list[tuple[str, int]] = []
    for label in frame["regime"].fillna("unknown").astype(str):
        if runs and runs[-1][0] == label:
            runs[-1] = (label, runs[-1][1] + 1)
        else:
            runs.append((label, 1))
    return runs
