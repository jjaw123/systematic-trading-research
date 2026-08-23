"""Tests for the monitoring package: logger, alerts, dashboard, wiring."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from rich.console import Console

from monitoring import history
from monitoring.alerts import Alert, AlertKind, AlertLevel, AlertManager
from monitoring.dashboard import Dashboard, _risk_bar
from monitoring.logger import get_context, set_context, setup_logging


class TestStructuredLogger:
    def _read_json_lines(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_entries_carry_trading_context(self, tmp_path) -> None:
        setup_logging(tmp_path, console=False)
        set_context(regime="bull", probability=0.85, equity=105_230.0,
                    positions=3, daily_pnl=340.0)
        logging.getLogger("regime_trader.test").info("hello %s", "world")
        entries = self._read_json_lines(tmp_path / "main.log")
        entry = entries[-1]
        assert entry["message"] == "hello world"
        assert entry["regime"] == "bull"
        assert entry["probability"] == 0.85
        assert entry["equity"] == 105_230.0
        assert entry["positions"] == 3
        assert entry["daily_pnl"] == 340.0
        assert "timestamp" in entry and entry["level"] == "INFO"

    def test_routing_to_dedicated_files(self, tmp_path) -> None:
        setup_logging(tmp_path, console=False)
        logging.getLogger("regime_trader.executor").info("order placed")
        logging.getLogger("regime_trader.hmm").warning("regime change")
        logging.getLogger("regime_trader.alerts").warning("alert sent")
        trades = self._read_json_lines(tmp_path / "trades.log")
        regime = self._read_json_lines(tmp_path / "regime.log")
        alerts = self._read_json_lines(tmp_path / "alerts.log")
        main = self._read_json_lines(tmp_path / "main.log")
        assert any(e["message"] == "order placed" for e in trades)
        assert any(e["message"] == "regime change" for e in regime)
        assert any(e["message"] == "alert sent" for e in alerts)
        # everything propagates to main.log too
        assert {e["message"] for e in main} >= {"order placed",
                                                "regime change", "alert sent"}

    def test_setup_is_idempotent(self, tmp_path) -> None:
        setup_logging(tmp_path, console=False)
        setup_logging(tmp_path, console=False)   # again — no dup handlers
        logging.getLogger("regime_trader.executor").info("once only")
        trades = self._read_json_lines(tmp_path / "trades.log")
        assert sum(e["message"] == "once only" for e in trades) == 1

    def test_context_getter(self) -> None:
        set_context(regime="crash")
        assert get_context()["regime"] == "crash"


class TestAlertManager:
    def _manager(self, **kw) -> tuple[AlertManager, list]:
        clock = {"now": datetime(2025, 6, 2, 14, 0, tzinfo=timezone.utc)}
        manager = AlertManager(console=False, now=lambda: clock["now"], **kw)
        return manager, clock

    def test_rate_limit_per_kind(self) -> None:
        manager, clock = self._manager(rate_limit_minutes=15)
        assert manager.send(AlertKind.REGIME_CHANGE, AlertLevel.INFO, "a")
        assert not manager.send(AlertKind.REGIME_CHANGE, AlertLevel.INFO, "b")
        # a different kind is not limited
        assert manager.send(AlertKind.LARGE_PNL, AlertLevel.WARNING, "c")
        # after the window the same kind goes through again
        clock["now"] += timedelta(minutes=16)
        assert manager.send(AlertKind.REGIME_CHANGE, AlertLevel.INFO, "d")

    def test_critical_bypasses_rate_limit(self) -> None:
        manager, _ = self._manager(rate_limit_minutes=15)
        assert manager.send(AlertKind.CIRCUIT_BREAKER, AlertLevel.CRITICAL, "x")
        assert manager.send(AlertKind.CIRCUIT_BREAKER, AlertLevel.CRITICAL, "y")

    def test_history_records_alerts(self) -> None:
        manager, _ = self._manager()
        manager.send(AlertKind.HMM_RETRAINED, AlertLevel.INFO, "trained",
                     n_regimes=4)
        history = manager.get_history()
        assert len(history) == 1
        assert isinstance(history[0], Alert)
        assert history[0].context == {"n_regimes": 4}

    def test_webhook_delivery(self, monkeypatch) -> None:
        captured = {}

        class FakeResponse:
            def read(self):
                return b"ok"

        def fake_urlopen(request, timeout=10):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode())
            return FakeResponse()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        manager, _ = self._manager(webhook_url="https://hooks.example/x")
        manager.send(AlertKind.DATA_FEED_DOWN, AlertLevel.WARNING,
                     "feed stale", symbol="SPY")
        assert captured["url"] == "https://hooks.example/x"
        assert captured["payload"]["kind"] == "data_feed_down"
        assert captured["payload"]["context"] == {"symbol": "SPY"}

    def test_delivery_failure_does_not_raise(self, monkeypatch) -> None:
        def boom(*a, **k):
            raise OSError("network down")

        monkeypatch.setattr("urllib.request.urlopen", boom)
        manager, _ = self._manager(webhook_url="https://hooks.example/x")
        assert manager.send(AlertKind.SYSTEM_ERROR, AlertLevel.CRITICAL, "z")


FULL_SNAPSHOT = {
    "timestamp": "2026-08-23T17:30:00+00:00", "date": "2026-08-23",
    "dry_run": False, "mode": "PAPER", "equity": 105_230.0,
    "session_start_equity": 104_890.0, "daily_pnl": 340.0,
    "daily_pnl_pct": 0.0032, "allocation": 0.95, "leverage": 1.25,
    "regime": "bull", "regime_confidence": 0.72, "regime_confirmed": True,
    "regime_stability": 14, "flicker_rate": 1.0, "flicker_window": 20,
    "breaker_status": "normal", "daily_dd": 0.003, "daily_dd_limit": 0.03,
    "peak_dd": 0.012, "peak_dd_limit": 0.10, "trades_today": 2,
    "positions": {"SPY": {"qty": 100, "entry_price": 514.0,
                          "current_price": 520.30, "stop": 508.0,
                          "unrealized_pnl": 630.0, "pnl_pct": 0.012,
                          "holding_days": 0.125, "regime_at_entry": "bull"}},
    "last_signals": [{"time": "14:30", "symbol": "SPY", "approved": True,
                      "strategy": "low_vol_bull", "qty": 20,
                      "reason": None, "modifications": []}],
    "feed_ok": True, "api_ok": True, "api_latency_ms": 23.0,
    "model_age_days": 2.0, "error": None,
}


class TestDashboard:
    def test_renders_all_sections(self) -> None:
        console = Console(record=True, width=100)
        Dashboard(refresh_seconds=0, console=console).update(
            FULL_SNAPSHOT, force=True)
        out = console.export_text()
        for fragment in ("REGIME", "PORTFOLIO", "POSITIONS", "RECENT SIGNALS",
                         "RISK STATUS", "SYSTEM", "BULL (72%)",
                         "Stability: 14 bars", "Flicker: 1/20",
                         "$105,230", "Allocation: 95%", "Leverage: 1.25x",
                         "Stop: $508.00", "3h", "14:30", "23ms", "PAPER"):
            assert fragment in out, f"missing: {fragment}"

    def test_throttle_and_force(self) -> None:
        console = Console(record=True, width=100)
        dash = Dashboard(refresh_seconds=3600, console=console)
        dash.update(FULL_SNAPSHOT)              # first render
        dash.update(FULL_SNAPSHOT)              # throttled
        dash.update(FULL_SNAPSHOT, force=True)  # forced
        assert console.export_text().count("REGIME") == 2

    def test_risk_bar_colors(self) -> None:
        assert "green" in _risk_bar(0.003, 0.03)      # 10% utilization
        assert "yellow" in _risk_bar(0.02, 0.03)      # 66%
        assert "red" in _risk_bar(0.029, 0.03)        # 96%
        assert "⛔" in _risk_bar(0.05, 0.03)          # breached
        assert _risk_bar(None, 0.03) == "n/a"


class TestHistory:
    def test_append_then_load_round_trip(self, tmp_path) -> None:
        path = history.history_path(tmp_path)
        history.append(path, FULL_SNAPSHOT)
        later = dict(FULL_SNAPSHOT, timestamp="2026-08-23T17:35:00+00:00",
                     equity=105_900.0)
        history.append(path, later)
        frame = history.load(path)
        assert list(frame["equity"]) == [105_230.0, 105_900.0]
        assert list(frame["regime"]) == ["bull", "bull"]
        # positions/signals are point-in-time and must not bloat the log
        assert "positions" not in frame.columns

    def test_load_skips_corrupt_lines(self, tmp_path) -> None:
        path = history.history_path(tmp_path)
        history.append(path, FULL_SNAPSHOT)
        with path.open("a") as handle:
            handle.write('{"timestamp": "truncated"\n')   # mid-write tail
        history.append(path, dict(FULL_SNAPSHOT,
                                  timestamp="2026-08-23T17:36:00+00:00"))
        assert len(history.load(path)) == 2

    def test_load_of_missing_file_is_empty_not_an_error(self, tmp_path) -> None:
        frame = history.load(tmp_path / "nope.jsonl")
        assert frame.empty and "equity" in frame.columns

    def test_append_without_timestamp_is_dropped(self, tmp_path) -> None:
        path = history.history_path(tmp_path)
        history.append(path, {"equity": 1.0})
        assert history.load(path).empty

    def test_load_sorts_by_time(self, tmp_path) -> None:
        path = history.history_path(tmp_path)
        for stamp in ("17:40", "17:20", "17:30"):
            history.append(path, dict(
                FULL_SNAPSHOT, timestamp=f"2026-08-23T{stamp}:00+00:00"))
        stamps = [t.strftime("%H:%M") for t in history.load(path)["timestamp"]]
        assert stamps == ["17:20", "17:30", "17:40"]

    def test_regime_runs_collapses_consecutive_labels(self, tmp_path) -> None:
        path = history.history_path(tmp_path)
        for i, regime in enumerate(["bull", "bull", "chop", "bull"]):
            history.append(path, dict(
                FULL_SNAPSHOT, regime=regime,
                timestamp=f"2026-08-23T17:{40 + i}:00+00:00"))
        assert history.regime_runs(history.load(path)) == [
            ("bull", 2), ("chop", 1), ("bull", 1)]

    def test_regime_runs_of_empty_frame(self) -> None:
        assert history.regime_runs(history.load(Path("nope.jsonl"))) == []

    def test_save_snapshot_also_records_history(self, tmp_path) -> None:
        from core.live_snapshot import save_snapshot

        save_snapshot(tmp_path / "state_snapshot.json", FULL_SNAPSHOT)
        assert len(history.load(history.history_path(tmp_path))) == 1


class TestLiveWiring:
    def test_cycle_sets_context_and_rich_snapshot(self, tmp_path) -> None:
        from test_live import make_system

        system, _, _ = make_system(tmp_path, "monitoring", dry_run=True)
        system.startup(wait_for_open=False)
        system._cycle_inner()
        ctx = get_context()
        assert ctx["equity"] == 100_000.0
        assert ctx["regime"] is not None
        snap = json.loads(system.snapshot_path.read_text())
        for key in ("allocation", "daily_dd_limit", "peak_dd_limit",
                    "model_age_days", "mode", "feed_ok", "api_ok"):
            assert key in snap
        assert snap["mode"] == "DRY RUN"
        assert snap["daily_dd_limit"] == 0.03

    def test_breaker_transition_sends_alert(self, tmp_path) -> None:
        from test_live import make_system

        system, _, _ = make_system(tmp_path, "alerting")
        system.alerts = AlertManager(console=False)
        system.startup(wait_for_open=False)
        system._cycle_inner()
        system.risk_manager.update_equity(100_000)
        system.risk_manager.update_equity(96_500)   # daily halt
        system._cycle_inner()
        kinds = [a.kind for a in system.alerts.get_history()]
        assert AlertKind.CIRCUIT_BREAKER in kinds
