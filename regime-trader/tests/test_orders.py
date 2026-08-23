"""Tests for the broker package: executor, tracker, client, data helpers.

Uses a hand-rolled FakeBroker matching the AlpacaClient surface — no
network, no credentials.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

from core.broker.alpaca_client import AlpacaClient, LIVE_CONFIRMATION
from core.broker.order_executor import OrderExecutor
from core.broker.position_tracker import PositionTracker
from core.data.market_data import parse_timeframe, validate_bars
from core.regime_strategies import Direction, Signal
from core.risk_manager import RiskManager


def make_signal(symbol: str = "SPY", entry: float = 100.0,
                stop: float = 95.0, take_profit: float | None = None,
                direction: Direction = Direction.LONG) -> Signal:
    return Signal(
        symbol=symbol, direction=direction, confidence=0.9,
        entry_price=entry, stop_loss=stop, take_profit=take_profit,
        position_size_pct=0.5, leverage=1.0, regime_id=0, regime_name="bull",
        regime_probability=0.9,
        timestamp=datetime(2025, 6, 2, tzinfo=timezone.utc),
        reasoning="test", strategy_name="test",
    )


class FakeBroker:
    """Stands in for AlpacaClient in executor/tracker tests."""

    def __init__(self) -> None:
        self.submitted: list = []          # raw request objects
        self.orders: dict[str, dict] = {}
        self.canceled: list[str] = []
        self.replaced: list[tuple] = []
        self.closed: list[str] = []
        self.closed_all = 0
        self.open_orders: list[dict] = []
        self.fill_order_after_polls: int | None = None
        self._polls = 0
        self.account = {"equity": 100_000.0, "cash": 100_000.0,
                        "buying_power": 200_000.0}
        self.broker_positions: list[dict] = []

    def submit_order(self, request):
        self.submitted.append(request)
        oid = f"order-{len(self.submitted)}"
        self.orders[oid] = {
            "id": oid, "client_order_id": request.client_order_id,
            "symbol": request.symbol, "qty": float(request.qty),
            "side": request.side.value, "status": "new",
            "limit_price": getattr(request, "limit_price", None),
            "stop_price": None, "filled_qty": 0.0,
            "filled_avg_price": None, "legs": [],
        }
        return dict(self.orders[oid])

    def get_order(self, order_id):
        self._polls += 1
        order = self.orders[order_id]
        if (self.fill_order_after_polls is not None
                and self._polls >= self.fill_order_after_polls
                and order["status"] == "new"):
            order.update(status="filled", filled_qty=order["qty"],
                         filled_avg_price=order["limit_price"] or 100.0)
        return dict(order)

    def cancel_order(self, order_id):
        self.canceled.append(order_id)
        self.orders[order_id]["status"] = "canceled"

    def replace_order(self, order_id, **changes):
        self.replaced.append((order_id, changes))
        return {"id": order_id, **changes}

    def list_orders(self, status="open", limit=200):
        return list(self.open_orders)

    def close_position(self, symbol):
        self.closed.append(symbol)
        return {"symbol": symbol, "status": "accepted"}

    def close_all_positions(self):
        self.closed_all += 1
        return []

    def get_account(self):
        return dict(self.account)

    def get_positions(self):
        return [dict(p) for p in self.broker_positions]


@pytest.fixture
def broker() -> FakeBroker:
    return FakeBroker()


def make_executor(broker: FakeBroker, **kw) -> OrderExecutor:
    """Executor with a fake clock: each sleep advances 1 simulated second."""
    state = {"t": 0.0}

    def clock() -> float:
        return state["t"]

    def sleep(s: float) -> None:
        state["t"] += s

    kw.setdefault("fill_timeout", 30.0)
    return OrderExecutor(broker, clock=clock, sleep=sleep, **kw)


class TestSubmitOrder:
    def test_limit_price_offset(self, broker) -> None:
        """Buys are priced +0.1% over reference; request is a LIMIT."""
        broker.fill_order_after_polls = 1
        ex = make_executor(broker)
        record = ex.submit_order(make_signal(entry=100.0), qty=50)
        req = broker.submitted[0]
        assert isinstance(req, LimitOrderRequest)
        assert float(req.limit_price) == pytest.approx(100.10)
        assert record.status == "filled"
        assert record.filled_qty == 50

    def test_unfilled_cancels_after_timeout_then_market(self, broker) -> None:
        """After 30 simulated seconds unfilled: cancel, then market retry."""
        ex = make_executor(broker)          # never fills
        record = ex.submit_order(make_signal(), qty=50, retry_market=True)
        assert broker.canceled == [record.order_id]
        assert "canceled" in record.notes[0]
        market_req = broker.submitted[1]
        assert isinstance(market_req, MarketOrderRequest)
        assert float(market_req.qty) == 50
        assert market_req.client_order_id == f"{record.trade_id}-mkt"
        assert record.child_order_ids == ["order-2"]

    def test_no_market_retry_when_disabled(self, broker) -> None:
        ex = make_executor(broker)
        ex.submit_order(make_signal(), qty=50, retry_market=False)
        assert len(broker.submitted) == 1
        assert len(broker.canceled) == 1

    def test_trade_id_links_signal_and_risk_decision(self, broker) -> None:
        broker.fill_order_after_polls = 1
        ex = make_executor(broker)
        sig = make_signal()
        rm = RiskManager(lock_file="/tmp/nonexistent-lock-test")
        decision = type("D", (), {"approved": True})()
        record = ex.submit_order(sig, qty=10, risk_decision=decision)
        assert broker.submitted[0].client_order_id == record.trade_id
        assert record.signal is sig
        assert record.risk_decision is decision
        assert ex.get_record(record.trade_id) is record

    def test_rejects_nonpositive_qty(self, broker) -> None:
        with pytest.raises(ValueError):
            make_executor(broker).submit_order(make_signal(), qty=0)


class TestBracketOrder:
    def test_bracket_carries_stop_and_take_profit(self, broker) -> None:
        ex = make_executor(broker)
        record = ex.submit_bracket_order(
            make_signal(entry=100.0, stop=95.0, take_profit=112.0), qty=10)
        req = broker.submitted[0]
        assert req.order_class.value == "bracket"
        assert float(req.stop_loss.stop_price) == 95.0
        assert float(req.take_profit.limit_price) == 112.0
        assert record.trade_id == req.client_order_id

    def test_take_profit_defaults_to_2r(self, broker) -> None:
        ex = make_executor(broker)
        ex.submit_bracket_order(make_signal(entry=100.0, stop=95.0), qty=10)
        req = broker.submitted[0]
        assert float(req.take_profit.limit_price) == pytest.approx(110.0)

    def test_bracket_requires_stop(self, broker) -> None:
        sig = make_signal()
        object.__setattr__(sig, "stop_loss", None)
        with pytest.raises(ValueError):
            make_executor(broker).submit_bracket_order(sig, qty=10)


class TestStopManagement:
    def test_modify_stop_only_tightens(self, broker) -> None:
        broker.open_orders = [{"id": "stop-1", "symbol": "SPY",
                               "stop_price": 95.0}]
        ex = make_executor(broker)
        assert ex.modify_stop("SPY", 97.0) is not None      # tighten: ok
        assert broker.replaced == [("stop-1", {"stop_price": 97.0})]
        assert ex.modify_stop("SPY", 93.0) is None          # widen: refused
        assert len(broker.replaced) == 1

    def test_modify_stop_without_stop_order(self, broker) -> None:
        assert make_executor(broker).modify_stop("SPY", 97.0) is None

    def test_close_position_and_all(self, broker) -> None:
        ex = make_executor(broker)
        ex.close_position("SPY")
        assert broker.closed == ["SPY"]
        ex.close_all_positions()
        assert broker.closed_all == 1


class TestPositionTracker:
    def test_sync_reconciles_with_broker(self, broker, tmp_path) -> None:
        broker.broker_positions = [
            {"symbol": "SPY", "qty": 100.0, "avg_entry_price": 400.0,
             "current_price": 410.0, "market_value": 41_000.0,
             "unrealized_pl": 1_000.0, "side": "long"},
        ]
        tracker = PositionTracker(
            broker, RiskManager(lock_file=tmp_path / "l.lock"))
        tracker.handle_trade_update({          # stale local position
            "event": "fill", "qty": 5, "price": 200.0,
            "order": {"symbol": "GONE", "side": "buy"}})
        tracker.sync()
        assert set(tracker.positions) == {"SPY"}
        assert tracker.positions["SPY"].qty == 100.0
        assert tracker.positions["SPY"].entry_price == 400.0

    def test_fill_updates_book_and_breaker(self, broker, tmp_path) -> None:
        rm = RiskManager(lock_file=tmp_path / "l.lock")
        tracker = PositionTracker(broker, rm)
        tracker.set_regime("bull")
        tracker.handle_trade_update({
            "event": "fill", "qty": 50, "price": 100.0,
            "order": {"symbol": "SPY", "side": "buy"}})
        pos = tracker.positions["SPY"]
        assert pos.qty == 50 and pos.entry_price == 100.0
        assert pos.regime_at_entry == "bull"
        assert tracker.trades_today == 1
        assert rm.breaker.day_start is not None     # equity fed to breaker
        # sell closes the position
        tracker.handle_trade_update({
            "event": "fill", "qty": 50, "price": 105.0,
            "order": {"symbol": "SPY", "side": "sell"}})
        assert "SPY" not in tracker.positions

    def test_partial_add_blends_entry_price(self, broker, tmp_path) -> None:
        tracker = PositionTracker(broker)
        for price in (100.0, 110.0):
            tracker.handle_trade_update({
                "event": "fill", "qty": 50, "price": price,
                "order": {"symbol": "SPY", "side": "buy"}})
        assert tracker.positions["SPY"].qty == 100
        assert tracker.positions["SPY"].entry_price == pytest.approx(105.0)

    def test_portfolio_state_for_risk_manager(self, broker, tmp_path) -> None:
        tracker = PositionTracker(
            broker, RiskManager(lock_file=tmp_path / "l.lock"))
        tracker.handle_trade_update({
            "event": "fill", "qty": 100, "price": 100.0,
            "order": {"symbol": "SPY", "side": "buy"}})
        state = tracker.portfolio_state(flicker_rate=2.0)
        assert state.equity == 100_000.0
        assert state.positions["SPY"].market_value == pytest.approx(10_000.0)
        assert state.flicker_rate == 2.0
        assert state.trades_today == 1


class TestAlpacaClientSafety:
    def test_from_env_defaults_to_paper(self, monkeypatch) -> None:
        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
        monkeypatch.delenv("ALPACA_PAPER", raising=False)
        client = AlpacaClient.from_env()
        assert client.paper is True

    def test_live_mode_requires_typed_confirmation(self, monkeypatch) -> None:
        monkeypatch.setenv("ALPACA_API_KEY", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
        monkeypatch.setenv("ALPACA_PAPER", "false")
        with pytest.raises(RuntimeError, match="not confirmed"):
            AlpacaClient.from_env(input_fn=lambda _: "yes")
        client = AlpacaClient.from_env(input_fn=lambda _: LIVE_CONFIRMATION)
        assert client.paper is False

    def test_missing_credentials_raise(self, monkeypatch) -> None:
        monkeypatch.delenv("ALPACA_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
        with pytest.raises(ValueError):
            AlpacaClient.from_env()

    def test_retry_with_exponential_backoff(self) -> None:
        delays: list[float] = []
        client = AlpacaClient("k", "s", max_retries=4,
                              sleep=delays.append)
        client._make_clients = lambda: None    # skip real reconnect
        attempts = {"n": 0}

        def flaky() -> str:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise ConnectionError("transient")
            return "ok"

        assert client._call(flaky) == "ok"
        assert delays == [1.0, 2.0]            # 1s then 2s backoff

    def test_retry_gives_up(self) -> None:
        client = AlpacaClient("k", "s", max_retries=3, sleep=lambda _: None)
        client._make_clients = lambda: None

        def always_fails() -> None:
            raise ConnectionError("down")

        with pytest.raises(ConnectionError, match="after 3 retries"):
            client._call(always_fails)


class TestMarketDataHelpers:
    def test_parse_timeframe(self) -> None:
        assert parse_timeframe("1Day").amount == 1
        assert parse_timeframe("5Min").amount == 5
        assert parse_timeframe("1Hour").unit_value.value == "Hour"
        with pytest.raises(ValueError):
            parse_timeframe("daily")

    def test_validate_bars_sorts_dedupes_and_drops_bad_rows(self) -> None:
        idx = pd.to_datetime(["2025-01-03", "2025-01-02", "2025-01-02",
                              "2025-01-06"], utc=True)
        bars = pd.DataFrame({
            "open": [10, 9, 9.5, -1], "high": [11, 10, 10.5, 1],
            "low": [9, 8, 8.5, 0.5], "close": [10.5, 9.5, 10.0, 0.9],
            "volume": [1e6] * 4,
        }, index=idx)
        out = validate_bars(bars, "TEST")
        assert out.index.is_monotonic_increasing
        assert not out.index.duplicated().any()
        assert (out[["open", "close"]] > 0).all().all()
        assert len(out) == 2   # dupe keeps last, negative-price row dropped
