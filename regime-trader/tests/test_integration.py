"""Integration tests: end-to-end pipeline, risk stress, recovery, paper API.

Everything except TestAlpacaPaperLifecycle runs the real pipeline (HMM,
strategies, risk, executor, tracker) over fakes. The paper-API class talks
to Alpaca's paper endpoint and auto-skips unless credentials are configured.
"""

import os
from datetime import timedelta

import pytest

from core.regime_strategies import Direction
from core.risk_manager import TradingStatus
from test_live import make_system
from test_risk import T0, make_signal, make_state


@pytest.fixture(scope="module")
def shared_dir(tmp_path_factory):
    """Module-shared dir: the HMM trains once, later systems load it."""
    return tmp_path_factory.mktemp("integration")


class TestEndToEndDryRun:
    """(a) data -> HMM -> strategy -> risk -> simulated orders."""

    def test_full_chain_dry_run(self, shared_dir) -> None:
        system, broker, _ = make_system(shared_dir, "e2e-dry", dry_run=True)
        system.startup(wait_for_open=False)
        system._cycle_inner()
        # every stage left evidence: regime, signals, risk verdicts, snapshot
        assert system.regime_state is not None
        assert system._last_signals, "strategy produced no signals"
        approved = [s for s in system._last_signals if s["approved"]]
        assert approved and all(s["qty"] > 0 for s in approved)
        assert broker.submitted == []          # dry run: nothing reaches broker
        assert system.snapshot_path.exists()

    def test_full_chain_live_links_audit_trail(self, shared_dir) -> None:
        """In live mode the same chain produces orders whose records link
        trade_id -> signal -> risk decision -> broker order."""
        system, broker, _ = make_system(shared_dir, "e2e-live")
        system.startup(wait_for_open=False)
        system._cycle_inner()
        assert broker.submitted, "no orders reached the broker"
        records = list(system.executor.records.values())
        assert records
        for record in records:
            assert record.trade_id.startswith("rt-")
            assert record.signal is not None
            assert record.risk_decision is not None
            assert record.risk_decision.approved
            assert record.qty == record.risk_decision.approved_qty


class TestRiskStressIntegration:
    """(c) extreme signals capped, rapid-fire blocked, no-stop rejected."""

    @pytest.fixture
    def rm(self, tmp_path):
        from core.risk_manager import RiskManager
        return RiskManager(lock_file=tmp_path / "lock")

    def test_extreme_signal_is_capped(self, rm) -> None:
        """A near-zero stop distance with absurd leverage cannot balloon
        past the single-position and leverage caps."""
        wild = make_signal(entry=100.0, stop=99.99, leverage=10.0)
        decision = rm.validate_signal(wild, make_state(equity=100_000))
        assert decision.approved
        assert decision.approved_value <= 0.15 * 100_000
        assert decision.modified_signal.leverage <= 1.25
        assert decision.approved_qty * 0.01 <= 0.01 * 100_000  # risk cap too

    def test_rapid_fire_orders_blocked(self, rm) -> None:
        """Burst of identical orders: one passes, the rest are duplicates."""
        outcomes = []
        for i in range(10):
            decision = rm.validate_signal(
                make_signal(), make_state(),
                now=T0 + timedelta(seconds=5 * i))
            outcomes.append(decision.approved)
        assert outcomes[0] is True
        assert not any(outcomes[1:])           # all within the 60s window

    def test_daily_trade_limit_backstop(self, rm) -> None:
        decision = rm.validate_signal(make_signal(),
                                      make_state(trades_today=20))
        assert not decision.approved
        assert "daily trade limit" in decision.rejection_reason

    def test_no_stop_no_trade(self, rm) -> None:
        decision = rm.validate_signal(make_signal(stop=None), make_state())
        assert not decision.approved
        assert "stop loss" in decision.rejection_reason


class TestRecovery:
    """(e) kill process, restart, verify state recovery and no double-entry."""

    def test_restart_reconciles_and_does_not_double_enter(self, shared_dir) -> None:
        # --- session A: trade, record the fill, snapshot, then "crash"
        # (no shutdown() — the snapshot from the last cycle is all that
        # survives, exactly like a killed process).
        system_a, broker_a, _ = make_system(shared_dir, "recovery")
        system_a.startup(wait_for_open=False)
        system_a._cycle_inner()
        assert broker_a.submitted
        record = next(iter(system_a.executor.records.values()))
        system_a.tracker.handle_trade_update({
            "event": "fill", "qty": record.filled_qty,
            "price": record.avg_fill_price,
            "order": {"symbol": "TEST", "side": "buy"}})
        system_a._save_snapshot()
        trades_before_crash = system_a.tracker.trades_today
        assert trades_before_crash >= 1

        # --- session B: same snapshot/model paths; the broker (source of
        # truth) now holds a position at the strategy's full target size.
        system_b, broker_b, market_data = make_system(shared_dir, "recovery")
        price = float(market_data.bars_map["TEST"]["close"].iloc[-1])
        qty = int(95_000 / price)
        broker_b.broker_positions = [{
            "symbol": "TEST", "qty": float(qty), "avg_entry_price": price,
            "current_price": price, "market_value": qty * price,
            "unrealized_pl": 0.0, "side": "long"}]
        system_b.startup(wait_for_open=False)

        # state recovered: same-day trade count and the broker's position
        assert system_b.tracker.trades_today == trades_before_crash
        assert set(system_b.tracker.positions) == {"TEST"}
        assert system_b.tracker.positions["TEST"].qty == qty

        # no double-entry: already at/above target allocation, so the next
        # cycle must not fire a fresh entry for the same exposure.
        system_b._cycle_inner()
        assert broker_b.submitted == []
        assert system_b.tracker.positions["TEST"].qty == qty  # book unchanged


requires_paper = pytest.mark.skipif(
    not (os.environ.get("ALPACA_API_KEY") and os.environ.get("ALPACA_SECRET_KEY"))
    or os.environ.get("ALPACA_PAPER", "true").strip().lower() == "false",
    reason="Alpaca paper credentials not configured (set ALPACA_API_KEY / "
           "ALPACA_SECRET_KEY in .env; never runs against live)",
)


@requires_paper
class TestAlpacaPaperLifecycle:
    """(d) real paper-API round trip: bracket, stop, cancel, clean state.

    Uses a 1-share limit order far below market so it can never fill, and
    always cleans up in finally.
    """

    def test_bracket_order_lifecycle(self) -> None:
        from dotenv import load_dotenv

        from core.broker.alpaca_client import AlpacaClient
        from core.broker.order_executor import OrderExecutor
        from core.data.market_data import MarketData
        from test_orders import make_signal as make_broker_signal

        load_dotenv()
        client = AlpacaClient.from_env(paper=True)   # paper forced
        client.connect()
        market_data = MarketData(client)
        snapshot = market_data.get_snapshot("SPY")
        last = snapshot["latest_price"] or snapshot["daily_close"]
        assert last and last > 0
        entry = round(last * 0.5, 2)                 # never fills
        signal = make_broker_signal(symbol="SPY", entry=entry,
                                    stop=round(entry * 0.9, 2))
        executor = OrderExecutor(client)
        record = executor.submit_bracket_order(signal, qty=1)
        try:
            order = client.get_order(record.order_id)
            assert order["status"] in ("new", "accepted", "pending_new",
                                       "held")
            assert order["legs"] or record.child_order_ids  # OCO legs exist
            # legs of an unfilled bracket are 'held', so there is no open
            # stop to tighten yet — modify_stop must refuse gracefully.
            assert executor.modify_stop("SPY", round(entry * 0.95, 2)) is None
        finally:
            try:
                executor.cancel_order(record.trade_id)
            except Exception:
                pass
        stale = [o for o in client.list_orders("open")
                 if o["client_order_id"] == record.trade_id]
        assert stale == [], "order still open after cancel"
