"""Volatility-regime allocation strategies.

DESIGN INSIGHT: the HMM detects VOLATILITY ENVIRONMENTS, not direction.
Calm markets trend up ~70% of the time; the worst drawdowns cluster in
high-volatility spikes. So:

- Low vol  -> fully invested with modest leverage (calm markets compound)
- Mid vol  -> stay invested while the trend holds, reduce when it breaks
- High vol -> reduce but stay partially invested (catch V-shaped rebounds)

Strategy assignment is by VOLATILITY RANK of each regime (ascending
``expected_volatility``), NOT by regime label — labels are sorted by return
and "BULL" does not mean low vol. The orchestrator ignores labels entirely.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd

from core.data.feature_engineering import true_range, wilder_smooth
from core.hmm_engine import RegimeInfo, RegimeLabel, RegimeState

logger = logging.getLogger("regime_trader.strategy")

#: Bars required before a strategy will emit a signal (50 EMA + headroom).
MIN_BARS_REQUIRED = 60

UNCERTAINTY_NOTE = "[UNCERTAINTY — size halved]"


class Direction(str, Enum):
    """Signal direction. Strategies are long-only: LONG or FLAT, never short."""

    LONG = "long"
    FLAT = "flat"


@dataclass(frozen=True)
class StrategyConfig:
    """Tunable strategy parameters (mirrors the ``strategy`` config section)."""

    low_vol_allocation: float = 0.95
    mid_vol_allocation_trend: float = 0.95
    mid_vol_allocation_no_trend: float = 0.60
    high_vol_allocation: float = 0.60
    low_vol_leverage: float = 1.25
    rebalance_threshold: float = 0.10
    uncertainty_size_mult: float = 0.50
    min_confidence: float = 0.55
    ema_window: int = 50
    atr_window: int = 14

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StrategyConfig":
        """Build from a settings dict, ignoring unknown keys."""
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass(frozen=True)
class Signal:
    """One per-symbol allocation instruction from a strategy."""

    symbol: str
    direction: Direction
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float | None
    position_size_pct: float      # target portfolio allocation, 0.60–0.95
    leverage: float               # 1.0, or 1.25 in low-vol regimes
    regime_id: int
    regime_name: str
    regime_probability: float
    timestamp: datetime | None
    reasoning: str
    strategy_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


def ema(close: pd.Series, span: int) -> pd.Series:
    """Causal exponential moving average."""
    return close.ewm(span=span, adjust=False, min_periods=span).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        window: int = 14) -> pd.Series:
    """Average true range (Wilder smoothing), causal."""
    return wilder_smooth(true_range(high, low, close), window)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

class BaseStrategy(ABC):
    """Interface for regime-conditioned allocation strategies.

    Args:
        config: Shared strategy parameters.
    """

    name: str = "base"

    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()

    @abstractmethod
    def generate_signal(self, symbol: str, bars: pd.DataFrame,
                        regime_state: RegimeState) -> Signal | None:
        """Produce an allocation signal for one symbol, or None when the
        bars are insufficient/invalid for the indicators."""

    # -------------------------------------------------------------- helpers

    def _context(self, symbol: str, bars: pd.DataFrame
                 ) -> tuple[float, float, float, datetime | None] | None:
        """Return (entry_price, ema, atr, timestamp) at the latest bar,
        or None when there isn't enough clean data."""
        for col in ("high", "low", "close"):
            if col not in bars.columns:
                logger.warning("%s: bars missing column '%s'", symbol, col)
                return None
        if len(bars) < max(MIN_BARS_REQUIRED, self.config.ema_window + 5):
            logger.debug("%s: only %d bars; need %d", symbol, len(bars),
                         MIN_BARS_REQUIRED)
            return None
        close = bars["close"]
        entry = float(close.iloc[-1])
        e = float(ema(close, self.config.ema_window).iloc[-1])
        a = float(atr(bars["high"], bars["low"], close,
                      self.config.atr_window).iloc[-1])
        if not (entry > 0 and a > 0 and pd.notna(e)):
            logger.warning("%s: degenerate indicators (entry=%s atr=%s ema=%s)",
                           symbol, entry, a, e)
            return None
        ts = bars.index[-1]
        timestamp = ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else None
        return entry, e, a, timestamp

    def _clamp_stop(self, stop: float, entry: float, atr_value: float) -> float:
        """Keep the stop strictly below entry: the raw EMA-based formulas can
        land above price when price has fallen far below the EMA, which would
        be an instantly-triggered stop on a new long."""
        return min(stop, entry - 0.5 * atr_value)

    def _signal(self, symbol: str, regime_state: RegimeState, *,
                entry: float, stop: float, allocation: float, leverage: float,
                timestamp: datetime | None, reasoning: str,
                metadata: dict[str, Any]) -> Signal:
        return Signal(
            symbol=symbol,
            direction=Direction.LONG,
            confidence=regime_state.probability,
            entry_price=entry,
            stop_loss=stop,
            take_profit=None,
            position_size_pct=allocation,
            leverage=leverage,
            regime_id=regime_state.state_id,
            regime_name=regime_state.label.value,
            regime_probability=regime_state.probability,
            timestamp=timestamp,
            reasoning=reasoning,
            strategy_name=self.name,
            metadata=metadata,
        )


class LowVolBullStrategy(BaseStrategy):
    """Lowest-vol third: fully invested with modest leverage.

    This is where most returns are generated — calm markets trend up, and
    calm + leverage = compounding. Stop: max(price - 3 ATR, EMA50 - 0.5 ATR).
    """

    name = "low_vol_bull"

    def generate_signal(self, symbol: str, bars: pd.DataFrame,
                        regime_state: RegimeState) -> Signal | None:
        ctx = self._context(symbol, bars)
        if ctx is None:
            return None
        entry, e, a, timestamp = ctx
        stop = self._clamp_stop(max(entry - 3.0 * a, e - 0.5 * a), entry, a)
        cfg = self.config
        return self._signal(
            symbol, regime_state, entry=entry, stop=stop,
            allocation=cfg.low_vol_allocation, leverage=cfg.low_vol_leverage,
            timestamp=timestamp,
            reasoning=(
                f"low-vol regime '{regime_state.label.value}' "
                f"(p={regime_state.probability:.2f}): calm conditions, "
                f"{cfg.low_vol_allocation:.0%} invested at "
                f"{cfg.low_vol_leverage}x leverage"
            ),
            metadata={"ema50": e, "atr": a},
        )


class MidVolCautiousStrategy(BaseStrategy):
    """Middle-vol third: invested while the trend holds, reduced when broken.

    Price above the 50 EMA keeps full allocation at 1.0x; below it,
    allocation drops to 60%. Stop: EMA50 - 0.5 ATR.
    """

    name = "mid_vol_cautious"

    def generate_signal(self, symbol: str, bars: pd.DataFrame,
                        regime_state: RegimeState) -> Signal | None:
        ctx = self._context(symbol, bars)
        if ctx is None:
            return None
        entry, e, a, timestamp = ctx
        cfg = self.config
        trend_intact = entry > e
        allocation = (cfg.mid_vol_allocation_trend if trend_intact
                      else cfg.mid_vol_allocation_no_trend)
        stop = self._clamp_stop(e - 0.5 * a, entry, a)
        trend_desc = ("trend intact (price > 50 EMA), staying invested"
                      if trend_intact
                      else "trend broken (price < 50 EMA), reducing")
        return self._signal(
            symbol, regime_state, entry=entry, stop=stop,
            allocation=allocation, leverage=1.0, timestamp=timestamp,
            reasoning=(
                f"mid-vol regime '{regime_state.label.value}' "
                f"(p={regime_state.probability:.2f}): {trend_desc} at "
                f"{allocation:.0%}"
            ),
            metadata={"ema50": e, "atr": a, "trend_intact": trend_intact},
        )


class HighVolDefensiveStrategy(BaseStrategy):
    """Highest-vol third: reduced but still invested — never short.

    Staying 60% invested catches the sharp V-shaped rebounds after selloffs.
    Stop: EMA50 - 1.0 ATR (wider for volatile conditions).
    """

    name = "high_vol_defensive"

    def generate_signal(self, symbol: str, bars: pd.DataFrame,
                        regime_state: RegimeState) -> Signal | None:
        ctx = self._context(symbol, bars)
        if ctx is None:
            return None
        entry, e, a, timestamp = ctx
        cfg = self.config
        stop = self._clamp_stop(e - 1.0 * a, entry, a)
        return self._signal(
            symbol, regime_state, entry=entry, stop=stop,
            allocation=cfg.high_vol_allocation, leverage=1.0,
            timestamp=timestamp,
            reasoning=(
                f"high-vol regime '{regime_state.label.value}' "
                f"(p={regime_state.probability:.2f}): defensive but staying "
                f"{cfg.high_vol_allocation:.0%} invested to catch rebounds"
            ),
            metadata={"ema50": e, "atr": a},
        )


# Backward-compatible aliases (label-flavored names from earlier designs).
CrashDefensiveStrategy = HighVolDefensiveStrategy
BearTrendStrategy = HighVolDefensiveStrategy
MeanReversionStrategy = MidVolCautiousStrategy
NeutralRangeStrategy = MidVolCautiousStrategy
BullTrendStrategy = LowVolBullStrategy
EuphoriaCautiousStrategy = LowVolBullStrategy

#: Label -> strategy fallback map. Used only when volatility metadata is
#: unavailable — the orchestrator's vol-rank mapping always takes precedence.
LABEL_TO_STRATEGY: dict[RegimeLabel, type[BaseStrategy]] = {
    RegimeLabel.CRASH: HighVolDefensiveStrategy,
    RegimeLabel.STRONG_BEAR: HighVolDefensiveStrategy,
    RegimeLabel.BEAR: HighVolDefensiveStrategy,
    RegimeLabel.WEAK_BEAR: MidVolCautiousStrategy,
    RegimeLabel.NEUTRAL: MidVolCautiousStrategy,
    RegimeLabel.WEAK_BULL: MidVolCautiousStrategy,
    RegimeLabel.BULL: LowVolBullStrategy,
    RegimeLabel.STRONG_BULL: LowVolBullStrategy,
    RegimeLabel.EUPHORIA: LowVolBullStrategy,
    RegimeLabel.UNKNOWN: HighVolDefensiveStrategy,
}


def vol_rank_position(rank: int, n_regimes: int) -> float:
    """Normalized vol rank: 0.0 = lowest-vol regime, 1.0 = highest."""
    if n_regimes <= 1:
        return 0.0
    return rank / (n_regimes - 1)


def strategy_class_for_vol_rank(position: float) -> type[BaseStrategy]:
    """Map a normalized vol rank to a strategy class (thirds)."""
    if position <= 0.33:
        return LowVolBullStrategy
    if position >= 0.67:
        return HighVolDefensiveStrategy
    return MidVolCautiousStrategy


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class StrategyOrchestrator:
    """Routes each detected regime to a strategy by volatility rank.

    Sorts the HMM's ``RegimeInfo``s by ``expected_volatility`` (ascending) —
    a sort that is INDEPENDENT of the return-based label sort — and maps each
    regime to Low/Mid/HighVol strategies by rank thirds. Labels are ignored.

    Args:
        config: StrategyConfig or a plain dict (the ``strategy`` settings
            section); unknown dict keys are ignored.
        regime_infos: Per-state metadata from ``HMMEngine.get_regime_info()``.
    """

    def __init__(self,
                 config: StrategyConfig | dict[str, Any] | None,
                 regime_infos: dict[int, RegimeInfo]) -> None:
        if isinstance(config, dict):
            self.config = StrategyConfig.from_dict(config)
        else:
            self.config = config or StrategyConfig()
        self._instances: dict[type[BaseStrategy], BaseStrategy] = {
            cls: cls(self.config)
            for cls in (LowVolBullStrategy, MidVolCautiousStrategy,
                        HighVolDefensiveStrategy)
        }
        self.regime_to_strategy: dict[int, BaseStrategy] = {}
        self.vol_rank: dict[int, float] = {}
        self.update_regime_infos(regime_infos)

    def update_regime_infos(self, regime_infos: dict[int, RegimeInfo]) -> None:
        """Rebuild the regime -> strategy mapping (call after HMM retrains)."""
        if not regime_infos:
            raise ValueError("regime_infos is empty")
        order = sorted(regime_infos, key=lambda r: regime_infos[r].expected_volatility)
        self.regime_to_strategy = {}
        self.vol_rank = {}
        n = len(order)
        for rank, rid in enumerate(order):
            pos = vol_rank_position(rank, n)
            cls = strategy_class_for_vol_rank(pos)
            self.regime_to_strategy[rid] = self._instances[cls]
            self.vol_rank[rid] = pos
            info = regime_infos[rid]
            logger.info(
                "regime %d ('%s', E[vol]=%.2f) -> vol_rank %.2f -> %s",
                rid, info.regime_name, info.expected_volatility, pos, cls.__name__,
            )

    def strategy_for_regime(self, regime_id: int) -> BaseStrategy:
        """Strategy instance assigned to a regime id."""
        try:
            return self.regime_to_strategy[regime_id]
        except KeyError:
            raise KeyError(
                f"regime {regime_id} unknown; call update_regime_infos() "
                "after retraining"
            ) from None

    def generate_signals(
        self,
        symbols: list[str],
        bars: dict[str, pd.DataFrame],
        regime_state: RegimeState,
        is_flickering: bool = False,
        current_allocations: dict[str, float] | None = None,
    ) -> list[Signal]:
        """Generate per-symbol signals for the current (confirmed) regime.

        Uncertainty mode (probability below ``min_confidence``, or the
        classifier flickering) halves position sizes and forces 1.0x
        leverage. When ``current_allocations`` is given, symbols whose
        target differs from the current allocation by no more than
        ``rebalance_threshold`` are skipped to prevent churn.
        """
        strategy = self.strategy_for_regime(regime_state.state_id)
        uncertain = (regime_state.probability < self.config.min_confidence
                     or is_flickering)
        signals: list[Signal] = []
        for symbol in symbols:
            sym_bars = bars.get(symbol)
            if sym_bars is None:
                logger.warning("no bars for %s; skipping", symbol)
                continue
            sig = strategy.generate_signal(symbol, sym_bars, regime_state)
            if sig is None:
                continue
            if uncertain:
                sig = self._apply_uncertainty(sig)
            if current_allocations is not None:
                current = current_allocations.get(symbol, 0.0)
                if not self.should_rebalance(current, sig.position_size_pct):
                    logger.debug(
                        "%s: target %.2f within %.0f%% of current %.2f; "
                        "no rebalance", symbol, sig.position_size_pct,
                        self.config.rebalance_threshold * 100, current,
                    )
                    continue
            signals.append(sig)
        return signals

    def should_rebalance(self, current_allocation: float,
                         target_allocation: float) -> bool:
        """True when target drifts from current by more than the threshold."""
        return abs(target_allocation - current_allocation) > self.config.rebalance_threshold

    def _apply_uncertainty(self, sig: Signal) -> Signal:
        """Halve size, force 1.0x leverage, and annotate the reasoning."""
        return replace(
            sig,
            position_size_pct=sig.position_size_pct * self.config.uncertainty_size_mult,
            leverage=1.0,
            reasoning=f"{sig.reasoning} {UNCERTAINTY_NOTE}",
            metadata={**sig.metadata, "uncertainty_mode": True},
        )


#: Backward-compatible alias for the earlier skeleton's ABC name.
BaseRegimeStrategy = BaseStrategy
