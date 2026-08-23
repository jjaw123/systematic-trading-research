"""Tests for core.regime_strategies: vol-rank mapping, allocations, filters."""

import numpy as np
import pandas as pd
import pytest

from core.hmm_engine import RegimeInfo, RegimeLabel, RegimeState
from core.regime_strategies import (
    CrashDefensiveStrategy,
    Direction,
    HighVolDefensiveStrategy,
    LowVolBullStrategy,
    MidVolCautiousStrategy,
    StrategyConfig,
    StrategyOrchestrator,
    UNCERTAINTY_NOTE,
    ema,
)


def make_info(regime_id: int, name: str, vol: float, ret: float = 0.0) -> RegimeInfo:
    return RegimeInfo(
        regime_id=regime_id, regime_name=name, expected_return=ret,
        expected_volatility=vol, recommended_strategy_type="",
        max_leverage_allowed=1.25, max_position_size_pct=0.15,
        min_confidence_to_act=0.55,
    )


def make_state(state_id: int = 0, prob: float = 0.90,
               label: RegimeLabel = RegimeLabel.BULL,
               confirmed: bool = True) -> RegimeState:
    return RegimeState(
        label=label, state_id=state_id, probability=prob,
        state_probabilities={state_id: prob}, timestamp=None,
        is_confirmed=confirmed, consecutive_bars=10,
    )


def trend_bars(n: int = 120, drift: float = 0.002) -> pd.DataFrame:
    """Deterministic geometric walk; positive drift ends above the 50 EMA,
    negative drift ends below it."""
    close = 100.0 * np.exp(np.cumsum(np.full(n, drift)))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame(
        {"open": open_, "high": close * 1.005, "low": close * 0.995,
         "close": close, "volume": np.full(n, 1e6)},
        index=pd.bdate_range("2024-01-02", periods=n),
    )


@pytest.fixture
def up_bars() -> pd.DataFrame:
    return trend_bars(drift=0.002)


@pytest.fixture
def down_bars() -> pd.DataFrame:
    return trend_bars(drift=-0.002)


class TestVolRankMapping:
    """Strategies are assigned by volatility rank, never by label."""

    def test_mapping_ignores_labels(self) -> None:
        """A high-vol 'euphoria'/'bull' regime must get the defensive
        strategy; a low-vol 'bear' must get the aggressive one."""
        infos = {
            0: make_info(0, "euphoria", vol=2.0),
            1: make_info(1, "bear", vol=0.3),
            2: make_info(2, "bull", vol=1.0),
            3: make_info(3, "crash", vol=1.5),
        }
        orch = StrategyOrchestrator(None, infos)
        # vol ranks: bear 0.0, bull 1/3, crash 2/3, euphoria 1.0 — with the
        # spec thresholds (<=0.33 / >=0.67) only the extremes leave MidVol.
        assert isinstance(orch.strategy_for_regime(1), LowVolBullStrategy)
        assert isinstance(orch.strategy_for_regime(2), MidVolCautiousStrategy)
        assert isinstance(orch.strategy_for_regime(3), MidVolCautiousStrategy)
        assert isinstance(orch.strategy_for_regime(0), HighVolDefensiveStrategy)

    def test_three_regime_thirds(self) -> None:
        infos = {i: make_info(i, f"r{i}", vol=v)
                 for i, v in enumerate([0.2, 1.0, 2.0])}
        orch = StrategyOrchestrator(None, infos)
        assert isinstance(orch.strategy_for_regime(0), LowVolBullStrategy)
        assert isinstance(orch.strategy_for_regime(1), MidVolCautiousStrategy)
        assert isinstance(orch.strategy_for_regime(2), HighVolDefensiveStrategy)
        assert orch.vol_rank == {0: 0.0, 1: 0.5, 2: 1.0}

    def test_update_after_retrain_rebuilds_mapping(self) -> None:
        infos = {i: make_info(i, f"r{i}", vol=v)
                 for i, v in enumerate([0.2, 1.0, 2.0])}
        orch = StrategyOrchestrator(None, infos)
        flipped = {i: make_info(i, f"r{i}", vol=v)
                   for i, v in enumerate([2.0, 1.0, 0.2])}
        orch.update_regime_infos(flipped)
        assert isinstance(orch.strategy_for_regime(0), HighVolDefensiveStrategy)
        assert isinstance(orch.strategy_for_regime(2), LowVolBullStrategy)

    def test_aliases_point_at_canonical_classes(self) -> None:
        assert CrashDefensiveStrategy is HighVolDefensiveStrategy


class TestStrategySignals:
    """Per-strategy allocation, leverage, and stop behavior."""

    def test_low_vol_bull(self, up_bars: pd.DataFrame) -> None:
        sig = LowVolBullStrategy().generate_signal("SPY", up_bars, make_state())
        assert sig is not None
        assert sig.direction is Direction.LONG
        assert sig.position_size_pct == 0.95
        assert sig.leverage == 1.25
        assert sig.stop_loss < sig.entry_price
        assert sig.strategy_name == "low_vol_bull"

    def test_mid_vol_trend_intact(self, up_bars: pd.DataFrame) -> None:
        sig = MidVolCautiousStrategy().generate_signal("SPY", up_bars, make_state())
        assert sig is not None
        assert up_bars["close"].iloc[-1] > ema(up_bars["close"], 50).iloc[-1]
        assert sig.position_size_pct == 0.95
        assert sig.leverage == 1.0
        assert sig.metadata["trend_intact"] is True

    def test_mid_vol_trend_broken(self, down_bars: pd.DataFrame) -> None:
        sig = MidVolCautiousStrategy().generate_signal("SPY", down_bars, make_state())
        assert sig is not None
        assert down_bars["close"].iloc[-1] < ema(down_bars["close"], 50).iloc[-1]
        assert sig.position_size_pct == 0.60
        assert sig.leverage == 1.0
        assert sig.metadata["trend_intact"] is False

    def test_high_vol_defensive_stays_long(self, down_bars: pd.DataFrame) -> None:
        sig = HighVolDefensiveStrategy().generate_signal("SPY", down_bars, make_state())
        assert sig is not None
        assert sig.direction is Direction.LONG  # never short
        assert sig.position_size_pct == 0.60
        assert sig.leverage == 1.0
        assert sig.stop_loss < sig.entry_price

    def test_stop_always_below_entry(self, down_bars: pd.DataFrame) -> None:
        """Even when price is far below the EMA, the stop is clamped under
        the entry price rather than instantly triggering."""
        for cls in (LowVolBullStrategy, MidVolCautiousStrategy,
                    HighVolDefensiveStrategy):
            sig = cls().generate_signal("SPY", down_bars, make_state())
            assert sig is not None and sig.stop_loss < sig.entry_price, cls

    def test_insufficient_bars_returns_none(self) -> None:
        sig = LowVolBullStrategy().generate_signal(
            "SPY", trend_bars(n=30), make_state()
        )
        assert sig is None


class TestUncertaintyMode:
    """Low confidence or flicker halves sizes and strips leverage."""

    @pytest.fixture
    def orch(self) -> StrategyOrchestrator:
        infos = {i: make_info(i, f"r{i}", vol=v)
                 for i, v in enumerate([0.2, 1.0, 2.0])}
        return StrategyOrchestrator(None, infos)

    def test_low_confidence_halves_size(self, orch: StrategyOrchestrator,
                                        up_bars: pd.DataFrame) -> None:
        state = make_state(state_id=0, prob=0.40)  # below 0.55 threshold
        [sig] = orch.generate_signals(["SPY"], {"SPY": up_bars}, state)
        assert sig.position_size_pct == pytest.approx(0.95 * 0.50)
        assert sig.leverage == 1.0
        assert sig.reasoning.endswith(UNCERTAINTY_NOTE)
        assert sig.metadata["uncertainty_mode"] is True

    def test_flicker_halves_size_even_when_confident(
        self, orch: StrategyOrchestrator, up_bars: pd.DataFrame
    ) -> None:
        state = make_state(state_id=0, prob=0.95)
        [sig] = orch.generate_signals(["SPY"], {"SPY": up_bars}, state,
                                      is_flickering=True)
        assert sig.position_size_pct == pytest.approx(0.95 * 0.50)
        assert sig.leverage == 1.0

    def test_confident_stable_regime_untouched(
        self, orch: StrategyOrchestrator, up_bars: pd.DataFrame
    ) -> None:
        state = make_state(state_id=0, prob=0.95)
        [sig] = orch.generate_signals(["SPY"], {"SPY": up_bars}, state)
        assert sig.position_size_pct == 0.95
        assert sig.leverage == 1.25
        assert UNCERTAINTY_NOTE not in sig.reasoning


class TestRebalancing:
    """Rebalance only when drift from target exceeds the threshold."""

    @pytest.fixture
    def orch(self) -> StrategyOrchestrator:
        infos = {0: make_info(0, "calm", vol=0.2)}
        return StrategyOrchestrator(None, infos)

    def test_should_rebalance_threshold(self, orch: StrategyOrchestrator) -> None:
        assert not orch.should_rebalance(0.90, 0.95)   # 5% drift: hold
        assert orch.should_rebalance(0.60, 0.95)       # 35% drift: rebalance
        assert not orch.should_rebalance(0.85, 0.95)   # exactly 10%: hold

    def test_generate_signals_skips_small_drift(
        self, orch: StrategyOrchestrator, up_bars: pd.DataFrame
    ) -> None:
        state = make_state(state_id=0, prob=0.95)
        signals = orch.generate_signals(
            ["SPY"], {"SPY": up_bars}, state,
            current_allocations={"SPY": 0.90},
        )
        assert signals == []  # target 0.95 vs current 0.90 -> no churn

    def test_generate_signals_emits_on_large_drift(
        self, orch: StrategyOrchestrator, up_bars: pd.DataFrame
    ) -> None:
        state = make_state(state_id=0, prob=0.95)
        signals = orch.generate_signals(
            ["SPY"], {"SPY": up_bars}, state,
            current_allocations={"SPY": 0.40},
        )
        assert len(signals) == 1


class TestConfig:
    def test_from_dict_ignores_unknown_keys(self) -> None:
        cfg = StrategyConfig.from_dict(
            {"low_vol_allocation": 0.9, "not_a_field": 1}
        )
        assert cfg.low_vol_allocation == 0.9
        assert cfg.rebalance_threshold == 0.10
