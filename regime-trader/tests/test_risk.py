"""Tests for core.risk_manager: sizing, caps, breakers, veto pipeline."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from core.hmm_engine import RegimeInfo, RegimeLabel
from core.regime_strategies import Direction, Signal
from core.risk_manager import (
    PortfolioState,
    PositionInfo,
    RiskManager,
    TradingStatus,
)

T0 = datetime(2025, 6, 2, 14, 30, tzinfo=timezone.utc)


def make_signal(symbol: str = "AAPL", entry: float = 100.0,
                stop: float | None = 95.0, leverage: float = 1.0,
                direction: Direction = Direction.LONG, prob: float = 0.90,
                metadata: dict | None = None) -> Signal:
    return Signal(
        symbol=symbol, direction=direction, confidence=prob,
        entry_price=entry, stop_loss=stop, take_profit=None,
        position_size_pct=0.95, leverage=leverage, regime_id=0,
        regime_name="bull", regime_probability=prob, timestamp=T0,
        reasoning="test", strategy_name="test", metadata=metadata or {},
    )


def make_state(equity: float = 100_000.0, positions: dict | None = None,
               **kw) -> PortfolioState:
    defaults = dict(cash=equity, buying_power=2 * equity,
                    peak_equity=equity)
    defaults.update(kw)
    return PortfolioState(equity=equity, positions=positions or {}, **defaults)


def held(symbol: str, value: float, sector: str | None = None) -> PositionInfo:
    return PositionInfo(symbol=symbol, qty=value / 100, market_value=value,
                        sector=sector)


@pytest.fixture
def rm(tmp_path) -> RiskManager:
    return RiskManager(lock_file=tmp_path / "trading_halted.lock")


class TestPositionSizing:
    def test_risk_per_trade_cap(self, rm) -> None:
        """Dollar risk never exceeds max_risk_per_trade * equity. With the
        default constants the overnight gap cap (2% / 3x) is strictly
        tighter than 1% risk sizing, so it binds: 2000 / (3 * 5) = 133."""
        d = rm.validate_signal(make_signal(entry=100, stop=95), make_state())
        assert d.approved
        assert d.approved_qty == 133
        assert d.approved_qty * 5 <= 0.01 * 100_000            # risk cap
        assert d.approved_qty * 3 * 5 <= 0.02 * 100_000        # gap cap

    def test_single_position_cap(self, rm) -> None:
        """Tight stops can't balloon notional past 15% of equity."""
        d = rm.validate_signal(make_signal(entry=100, stop=99.9), make_state())
        assert d.approved
        assert d.approved_value <= 0.15 * 100_000
        assert any("single-position" in m for m in d.modifications)

    def test_stop_not_below_entry_rejected(self, rm) -> None:
        d = rm.validate_signal(make_signal(entry=100, stop=100), make_state())
        assert not d.approved and "stop" in d.rejection_reason

    def test_missing_stop_rejected(self, rm) -> None:
        """System refuses orders without a stop loss."""
        d = rm.validate_signal(make_signal(stop=None), make_state())
        assert not d.approved and "stop loss" in d.rejection_reason

    def test_minimum_position_value(self, rm) -> None:
        d = rm.validate_signal(make_signal(entry=90, stop=1.0),
                               make_state(equity=9_000))
        assert not d.approved and "minimum" in d.rejection_reason

    def test_gap_risk_caps_overnight_size(self, rm) -> None:
        """3x gap-through of the stop must cost <= 2% of equity."""
        d = rm.validate_signal(make_signal(entry=100, stop=90), make_state())
        assert d.approved
        assert d.approved_qty == 66           # 2000 / (3 * 10)
        assert d.approved_qty * 3 * 10 <= 0.02 * 100_000
        assert any("gap-risk" in m for m in d.modifications)

    def test_regime_cap_applies_before_portfolio_cap(self, rm) -> None:
        info = RegimeInfo(0, "crash", -1.0, 2.0, "defensive", 0.0, 0.05, 0.70)
        d = rm.validate_signal(make_signal(entry=100, stop=99.5),
                               make_state(), regime_info=info)
        assert d.approved
        assert d.approved_value <= 0.05 * 100_000
        assert any("regime cap" in m for m in d.modifications)


class TestPortfolioLimits:
    def test_max_exposure_blocks_new_trades(self, rm) -> None:
        state = make_state(positions={"SPY": held("SPY", 80_000)})
        d = rm.validate_signal(make_signal(), state)
        assert not d.approved and "exposure" in d.rejection_reason

    def test_exposure_headroom_clips(self, rm) -> None:
        state = make_state(positions={"SPY": held("SPY", 70_000)})
        d = rm.validate_signal(make_signal(entry=100, stop=99), state)
        assert d.approved
        assert d.approved_value <= 10_000 + 100
        assert any("headroom" in m for m in d.modifications)

    def test_max_concurrent_positions(self, rm) -> None:
        positions = {s: held(s, 1_000) for s in "ABCDE"}
        d = rm.validate_signal(make_signal(symbol="NEW"),
                               make_state(positions=positions))
        assert not d.approved and "concurrent" in d.rejection_reason
        # adding to an existing position is still allowed
        d2 = rm.validate_signal(make_signal(symbol="A"),
                                make_state(positions=positions))
        assert d2.approved

    def test_daily_trade_limit(self, rm) -> None:
        d = rm.validate_signal(make_signal(), make_state(trades_today=20))
        assert not d.approved and "daily trade limit" in d.rejection_reason

    def test_sector_concentration(self, rm) -> None:
        sector_map = {"NVDA": "tech", "AMD": "tech"}
        state = make_state(positions={"AMD": held("AMD", 30_000, "tech")})
        d = rm.validate_signal(make_signal(symbol="NVDA"), state,
                               sector_map=sector_map)
        assert not d.approved and "sector" in d.rejection_reason

    def test_duplicate_orders_blocked(self, rm) -> None:
        assert rm.validate_signal(make_signal(), make_state(), now=T0).approved
        dup = rm.validate_signal(make_signal(), make_state(),
                                 now=T0 + timedelta(seconds=30))
        assert not dup.approved and "duplicate" in dup.rejection_reason
        later = rm.validate_signal(make_signal(), make_state(),
                                   now=T0 + timedelta(seconds=90))
        assert later.approved

    def test_spread_and_tradable_checks(self, rm) -> None:
        wide = {"bid": 100.0, "ask": 101.0, "tradable": True}   # 1% spread
        d = rm.validate_signal(make_signal(), make_state(), quote=wide)
        assert not d.approved and "spread" in d.rejection_reason
        halted_sym = {"bid": 100.0, "ask": 100.05, "tradable": False}
        d2 = rm.validate_signal(make_signal(), make_state(), quote=halted_sym)
        assert not d2.approved and "tradable" in d2.rejection_reason
        tight = {"bid": 100.0, "ask": 100.05, "tradable": True}
        assert rm.validate_signal(make_signal(), make_state(), quote=tight).approved

    def test_buying_power_clips(self, rm) -> None:
        d = rm.validate_signal(make_signal(entry=100, stop=95),
                               make_state(buying_power=5_000))
        assert d.approved and d.approved_value <= 5_000
        assert any("buying power" in m for m in d.modifications)

    def test_flat_signal_always_allowed(self, rm) -> None:
        rm.update_equity(100_000, timestamp=T0)
        rm.update_equity(96_500, timestamp=T0)      # daily halt
        d = rm.validate_signal(make_signal(direction=Direction.FLAT, stop=None),
                               make_state())
        assert d.approved


class TestCircuitBreakers:
    def test_daily_reduce_then_halt(self, rm) -> None:
        rm.update_equity(100_000, timestamp=T0)
        assert rm.update_equity(97_900) is TradingStatus.REDUCED   # -2.1%
        d = rm.validate_signal(make_signal(entry=100, stop=95), make_state())
        assert d.approved and d.approved_qty == 66                 # 133 halved
        assert rm.update_equity(96_900) is TradingStatus.HALTED    # -3.1%
        d2 = rm.validate_signal(make_signal(), make_state())
        assert not d2.approved and "circuit breaker" in d2.rejection_reason

    def test_status_never_relaxes_intraday(self, rm) -> None:
        rm.update_equity(100_000)
        rm.update_equity(96_500)                                   # halt
        assert rm.update_equity(99_800) is TradingStatus.HALTED    # recovered,
        rm.breaker.reset_daily(99_800)                             # still halted
        assert rm.breaker.status is TradingStatus.NORMAL

    def test_weekly_breakers_survive_daily_reset(self, rm) -> None:
        rm.update_equity(100_000)
        assert rm.update_equity(94_500) is TradingStatus.HALTED    # daily -5.5%
        rm.breaker.reset_daily(94_500)
        assert rm.breaker.status is TradingStatus.REDUCED          # weekly -5.5%
        assert rm.update_equity(92_900) is TradingStatus.HALTED    # weekly -7.1%
        rm.breaker.reset_daily(92_900)
        assert rm.breaker.status is TradingStatus.HALTED           # weekly holds
        rm.breaker.reset_weekly(92_900)
        assert rm.breaker.status is TradingStatus.NORMAL

    def test_peak_stop_writes_lock_file(self, rm, tmp_path) -> None:
        lock = tmp_path / "trading_halted.lock"
        rm.update_equity(100_000, regime_label="bull", open_positions=3)
        assert rm.update_equity(89_500) is TradingStatus.STOPPED   # -10.5%
        assert lock.exists()
        assert not rm.validate_signal(make_signal(), make_state()).approved
        # a fresh manager sees the lock and starts STOPPED
        rm2 = RiskManager(lock_file=lock)
        assert rm2.breaker.status is TradingStatus.STOPPED
        # manual deletion resumes with a fresh risk budget
        lock.unlink()
        assert rm.update_equity(89_500) is TradingStatus.NORMAL

    def test_breaker_history_records_regime(self, rm) -> None:
        rm.update_equity(100_000, regime_label="euphoria")
        rm.update_equity(97_100, regime_label="euphoria", open_positions=2)
        events = rm.breaker.get_history()
        assert len(events) == 1
        ev = events[0]
        assert ev.breaker_type == "daily_reduce"
        assert ev.regime_label == "euphoria"
        assert ev.positions_closed == 2
        assert ev.drawdown == pytest.approx(0.029)


class TestLeverage:
    def test_low_vol_leverage_allowed_when_calm(self, rm) -> None:
        d = rm.validate_signal(make_signal(leverage=1.25), make_state())
        assert d.approved and d.modified_signal.leverage == 1.25

    def test_leverage_capped_at_max(self, rm) -> None:
        d = rm.validate_signal(make_signal(leverage=2.0), make_state())
        assert d.approved and d.modified_signal.leverage == 1.25

    def test_three_positions_force_1x(self, rm) -> None:
        positions = {s: held(s, 1_000) for s in "ABC"}
        d = rm.validate_signal(make_signal(leverage=1.25),
                               make_state(positions=positions))
        assert d.approved and d.modified_signal.leverage == 1.0
        assert any("leverage forced" in m for m in d.modifications)

    def test_breaker_forces_1x(self, rm) -> None:
        rm.update_equity(100_000)
        rm.update_equity(97_500)                                   # REDUCED
        d = rm.validate_signal(make_signal(leverage=1.25), make_state())
        assert d.approved and d.modified_signal.leverage == 1.0

    def test_uncertainty_and_flicker_force_1x(self, rm) -> None:
        d = rm.validate_signal(
            make_signal(leverage=1.25, metadata={"uncertainty_mode": True}),
            make_state())
        assert d.modified_signal.leverage == 1.0
        d2 = rm.validate_signal(make_signal(symbol="MSFT", leverage=1.25),
                                make_state(flicker_rate=5.0))
        assert d2.modified_signal.leverage == 1.0


class TestCorrelation:
    @staticmethod
    def _history(rho: float, n: int = 90, seed: int = 3) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        x = rng.normal(0, 0.01, n)
        z = rng.normal(0, 0.01, n)
        y = rho * x + np.sqrt(1 - rho ** 2) * z
        idx = pd.bdate_range("2025-01-01", periods=n)
        return pd.DataFrame({
            "AAPL": 100 * np.cumprod(1 + x),
            "MSFT": 100 * np.cumprod(1 + y),
        }, index=idx)

    def test_high_correlation_rejects(self, rm) -> None:
        hist = self._history(rho=0.99)
        state = make_state(positions={"MSFT": held("MSFT", 10_000)})
        d = rm.validate_signal(make_signal(symbol="AAPL"), state,
                               price_history=hist)
        assert not d.approved and "correlation" in d.rejection_reason

    def test_moderate_correlation_halves(self, rm) -> None:
        hist = self._history(rho=0.78)
        actual = hist.pct_change().tail(60)["AAPL"].corr(
            hist.pct_change().tail(60)["MSFT"])
        assert 0.70 < actual <= 0.85          # precondition for this seed
        state = make_state(positions={"MSFT": held("MSFT", 10_000)})
        d = rm.validate_signal(make_signal(symbol="AAPL", entry=100, stop=95),
                               state, price_history=hist)
        assert d.approved and d.approved_qty == 66      # 133 halved
        assert any("correlation" in m for m in d.modifications)

    def test_low_correlation_untouched(self, rm) -> None:
        hist = self._history(rho=0.0)
        state = make_state(positions={"MSFT": held("MSFT", 10_000)})
        d = rm.validate_signal(make_signal(symbol="AAPL", entry=100, stop=95),
                               state, price_history=hist)
        assert d.approved and d.approved_qty == 133     # gap cap only
