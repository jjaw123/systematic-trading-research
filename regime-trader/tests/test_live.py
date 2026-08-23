"""Tests for core.live_engine: startup, cycle, error posture, shutdown.

Runs the real pipeline (HMM, strategies, risk, executor) over fakes for the
broker and market data — no network, no credentials.
"""

import time
from datetime import datetime, timezone

import pandas as pd
import pytest

from core.live_engine import TradingSystem
from core.risk_manager import RiskManager, TradingStatus
from test_look_ahead import make_bars
from test_orders import FakeBroker, make_executor


class FakeBrokerLive(FakeBroker):
    """FakeBroker plus the clock/market surface the live loop uses."""

    def get_clock(self):
        return {"is_open": True, "next_open": None, "next_close": None,
                "timestamp": datetime.now(timezone.utc)}

    def is_market_open(self):
        return True


class FakeMarketData:
    """Serves canned daily bars and quotes; records stream calls."""

    def __init__(self, bars_map: dict[str, pd.DataFrame]) -> None:
        self.bars_map = bars_map
        self.subscribed: list = []
        self.stream_started = 0
        self.stream_stopped = 0

    def get_historical_bars(self, symbols, start, end=None, timeframe=None):
        if isinstance(symbols, str):
            return self.bars_map[symbols].copy()
        return {s: self.bars_map[s].copy() for s in symbols}

    def get_latest_quote(self, symbol):
        close = float(self.bars_map[symbol]["close"].iloc[-1])
        return {"symbol": symbol, "bid": close * 0.9999,
                "ask": close * 1.0001, "spread_pct": 0.0002,
                "tradable": True}

    def subscribe_bars(self, symbols, callback):
        self.subscribed.append(list(symbols))

    def start_stream(self):
        self.stream_started += 1

    def stop_stream(self):
        self.stream_stopped += 1


def make_settings() -> dict:
    return {
        "broker": {"paper_trading": True, "symbols": ["TEST"],
                   "timeframe": "1Day", "cycle_seconds": 1},
        "hmm": {"n_candidates": [3], "n_init": 2, "covariance_type": "full",
                "min_train_bars": 300, "retrain_interval_bars": 5000,
                "stability_bars": 3, "flicker_window": 20,
                "flicker_threshold": 4, "min_confidence": 0.55},
        "strategy": {"rebalance_threshold": 0.10},
        "risk": {},
        "backtest": {},
        "monitoring": {"dashboard_refresh_seconds": 5,
                       "alert_rate_limit_minutes": 15},
    }


@pytest.fixture(scope="module")
def shared_dir(tmp_path_factory):
    """Module-shared dir so the HMM trains once and later tests load it."""
    return tmp_path_factory.mktemp("live")


def make_system(shared_dir, name: str, dry_run: bool = False):
    broker = FakeBrokerLive()
    broker.fill_order_after_polls = 1
    market_data = FakeMarketData({"TEST": make_bars(1300)})
    risk_manager = RiskManager(lock_file=shared_dir / f"{name}.lock")
    system = TradingSystem(
        make_settings(), dry_run=dry_run,
        snapshot_path=shared_dir / f"{name}-snapshot.json",
        model_path=shared_dir / "hmm_model.pkl",   # shared: train once
        client=broker, market_data=market_data,
        risk_manager=risk_manager,
        executor=make_executor(broker),
        sleep=lambda _: None,
    )
    return system, broker, market_data


class TestStartup:
    def test_startup_trains_and_saves_model(self, shared_dir) -> None:
        system, _, market_data = make_system(shared_dir, "startup")
        system.startup(wait_for_open=False)
        assert system.model_path.exists()
        assert system.engine is not None
        assert system.orchestrator is not None
        assert market_data.subscribed == [["TEST"]]
        assert market_data.stream_started == 1
        assert system.session_start_equity == 100_000.0

    def test_second_startup_loads_saved_model(self, shared_dir) -> None:
        system, _, _ = make_system(shared_dir, "reload")
        system.startup(wait_for_open=False)
        first_trained = None
        from core.hmm_engine import HMMEngine
        first_trained = HMMEngine.load(system.model_path).metadata["training_date"]
        assert system.engine.metadata["training_date"] == first_trained

    def test_exits_when_closed_and_no_wait(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "closed")
        broker.get_clock = lambda: {"is_open": False, "next_open": "tomorrow",
                                    "next_close": None, "timestamp": None}
        with pytest.raises(SystemExit):
            system.startup(wait_for_open=False)


class TestCycle:
    def test_dry_run_evaluates_but_submits_nothing(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "dry", dry_run=True)
        system.startup(wait_for_open=False)
        system._cycle_inner()
        assert broker.submitted == []
        assert system.regime_state is not None
        assert system.snapshot_path.exists()
        assert any(s["approved"] for s in system._last_signals)

    def test_live_submits_approved_orders(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "live")
        system.startup(wait_for_open=False)
        system._cycle_inner()
        assert len(broker.submitted) >= 1
        req = broker.submitted[0]
        assert req.symbol == "TEST"
        assert req.client_order_id.startswith("rt-")

    def test_stale_feed_pauses_signals(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "stale")
        system.startup(wait_for_open=False)
        system.last_feed_event = time.time() - 1000   # stream went silent
        system._cycle_inner()
        assert broker.submitted == []                  # paused
        assert system.snapshot_path.exists()           # loop still healthy

    def test_hmm_failure_holds_previous_regime(self, shared_dir, monkeypatch) -> None:
        system, _, _ = make_system(shared_dir, "hmmfail", dry_run=True)
        system.startup(wait_for_open=False)
        system._cycle_inner()
        previous = system.regime_state
        assert previous is not None

        def boom(_features):
            raise RuntimeError("degenerate covariance")

        monkeypatch.setattr(system.engine, "predict", boom)
        system.cycle()                                 # must not raise
        assert system.regime_state is previous         # held

    def test_breaker_halt_closes_all_positions_once(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "halt")
        system.startup(wait_for_open=False)
        system._cycle_inner()
        assert broker.closed_all == 0
        system.risk_manager.update_equity(100_000)
        system.risk_manager.update_equity(96_500)      # daily halt (-3.5%)
        system._cycle_inner()
        assert broker.closed_all == 1
        system._cycle_inner()                          # no repeat close
        assert broker.closed_all == 1

    def test_trailing_stop_tightens_open_position(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "stops")
        system.startup(wait_for_open=False)
        price = float(system.market_data.bars_map["TEST"]["close"].iloc[-1])
        system.tracker.handle_trade_update({
            "event": "fill", "qty": 100, "price": price,
            "order": {"symbol": "TEST", "side": "buy"}})
        broker.open_orders = [{"id": "stop-1", "symbol": "TEST",
                               "stop_price": price * 0.01}]  # far too loose
        system._cycle_inner()
        assert len(broker.replaced) == 1
        _, changes = broker.replaced[0]
        assert changes["stop_price"] > price * 0.01
        assert system.tracker.positions["TEST"].stop_level == changes["stop_price"]


class TestShutdownAndRecovery:
    def test_shutdown_saves_state_and_keeps_positions(self, shared_dir) -> None:
        system, broker, market_data = make_system(shared_dir, "shutdown")
        system.startup(wait_for_open=False)
        system.tracker.handle_trade_update({
            "event": "fill", "qty": 10, "price": 50.0,
            "order": {"symbol": "TEST", "side": "buy"}})
        system.shutdown()
        assert broker.closed == [] and broker.closed_all == 0  # kept open
        assert market_data.stream_stopped == 1
        assert system.snapshot_path.exists()

    def test_snapshot_restores_same_day_counters(self, shared_dir) -> None:
        system, _, _ = make_system(shared_dir, "recover")
        system.startup(wait_for_open=False)
        system.tracker.trades_today = 7
        system._save_snapshot()

        system2, _, _ = make_system(shared_dir, "recover")  # same snapshot
        system2.startup(wait_for_open=False)
        assert system2.tracker.trades_today == 7
