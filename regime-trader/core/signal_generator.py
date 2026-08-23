"""Signal generation: combines HMM regime output with allocation strategy.

The SignalGenerator is the orchestration point between regime detection,
strategy allocation targets, and risk limits. It emits concrete, per-symbol
trade signals that the order executor can act on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd

from core.hmm_engine import HMMEngine, RegimeState
from core.regime_strategies import BaseRegimeStrategy
from core.risk_manager import RiskManager


class SignalAction(Enum):
    """Concrete action a signal requests."""

    BUY = "buy"
    SELL = "sell"
    REBALANCE = "rebalance"
    HOLD = "hold"
    FLATTEN = "flatten"


@dataclass(frozen=True)
class Signal:
    """A single per-symbol trade instruction.

    Attributes:
        symbol: Ticker the signal applies to.
        action: Requested action.
        target_weight: Desired portfolio weight after execution.
        confidence: Regime confidence carried through for sizing/telemetry.
        regime_state: The regime context that produced this signal.
        timestamp: Bar time the signal was generated for.
        reason: Human-readable explanation for logging.
    """

    symbol: str
    action: SignalAction
    target_weight: float
    confidence: float
    regime_state: RegimeState
    timestamp: datetime
    reason: str = ""


@dataclass
class SignalBatch:
    """All signals for one evaluation cycle, plus portfolio context."""

    timestamp: datetime
    signals: list[Signal] = field(default_factory=list)
    gross_target: float = 0.0


class SignalGenerator:
    """Produces trade signals from regime state, strategy, and risk gates.

    Args:
        hmm_engine: Fitted regime detection engine.
        strategy: Allocation strategy conditioned on regimes.
        risk_manager: Risk gate applied to every emitted signal.
        symbols: Trading universe.
    """

    def __init__(
        self,
        hmm_engine: HMMEngine,
        strategy: BaseRegimeStrategy,
        risk_manager: RiskManager,
        symbols: list[str],
    ) -> None:
        self.hmm_engine = hmm_engine
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.symbols = symbols

    def generate(
        self,
        features: pd.DataFrame,
        current_weights: dict[str, float],
        equity: float,
    ) -> SignalBatch:
        """Run one full evaluation cycle and emit signals.

        Steps: classify regime → get allocation target → diff against current
        weights → apply risk gates → emit per-symbol signals.

        Args:
            features: Feature matrix ending at the decision bar (no future
                data).
            current_weights: Current portfolio weights by symbol.
            equity: Current account equity.

        Returns:
            A :class:`SignalBatch` for the executor (possibly all HOLDs).
        """
        raise NotImplementedError

    def _detect_trend(self, features: pd.DataFrame) -> bool:
        """Return True when the trend filter confirms directional exposure."""
        raise NotImplementedError

    def _target_weights(
        self, gross_target: float, current_weights: dict[str, float]
    ) -> dict[str, float]:
        """Distribute the gross allocation target across the universe."""
        raise NotImplementedError
