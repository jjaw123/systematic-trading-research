"""Regime type definitions: labels, label sets, policies, and dataclasses.

Split out of hmm_engine.py so the engine stays focused on model fitting and
inference; hmm_engine re-exports everything here, so
``from core.hmm_engine import RegimeLabel, RegimeState, ...`` keeps working.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RegimeLabel(str, Enum):
    """Descriptive regime names, assigned by ascending mean return."""

    CRASH = "crash"
    STRONG_BEAR = "strong_bear"
    BEAR = "bear"
    WEAK_BEAR = "weak_bear"
    NEUTRAL = "neutral"
    WEAK_BULL = "weak_bull"
    BULL = "bull"
    STRONG_BULL = "strong_bull"
    EUPHORIA = "euphoria"
    UNKNOWN = "unknown"


#: Backward-compatible alias for earlier skeleton imports.
Regime = RegimeLabel

#: Label assignment per selected state count, ordered by ascending mean return.
LABEL_SETS: dict[int, list[RegimeLabel]] = {
    3: [RegimeLabel.BEAR, RegimeLabel.NEUTRAL, RegimeLabel.BULL],
    4: [RegimeLabel.CRASH, RegimeLabel.BEAR, RegimeLabel.BULL,
        RegimeLabel.EUPHORIA],
    5: [RegimeLabel.CRASH, RegimeLabel.BEAR, RegimeLabel.NEUTRAL,
        RegimeLabel.BULL, RegimeLabel.EUPHORIA],
    6: [RegimeLabel.CRASH, RegimeLabel.STRONG_BEAR, RegimeLabel.WEAK_BEAR,
        RegimeLabel.WEAK_BULL, RegimeLabel.STRONG_BULL, RegimeLabel.EUPHORIA],
    7: [RegimeLabel.CRASH, RegimeLabel.STRONG_BEAR, RegimeLabel.WEAK_BEAR,
        RegimeLabel.NEUTRAL, RegimeLabel.WEAK_BULL, RegimeLabel.STRONG_BULL,
        RegimeLabel.EUPHORIA],
}

#: Default per-label policy: (strategy_type, max_leverage, max_pos_pct, min_conf).
LABEL_POLICY: dict[RegimeLabel, tuple[str, float, float, float]] = {
    RegimeLabel.CRASH: ("defensive", 0.0, 0.05, 0.70),
    RegimeLabel.STRONG_BEAR: ("defensive", 0.50, 0.05, 0.65),
    RegimeLabel.BEAR: ("mean_reversion", 0.75, 0.08, 0.60),
    RegimeLabel.WEAK_BEAR: ("mean_reversion", 1.00, 0.10, 0.60),
    RegimeLabel.NEUTRAL: ("mean_reversion", 1.00, 0.10, 0.55),
    RegimeLabel.WEAK_BULL: ("trend_following", 1.00, 0.12, 0.55),
    RegimeLabel.BULL: ("trend_following", 1.25, 0.15, 0.55),
    RegimeLabel.STRONG_BULL: ("trend_following", 1.25, 0.15, 0.55),
    RegimeLabel.EUPHORIA: ("trend_following", 1.00, 0.10, 0.60),
    RegimeLabel.UNKNOWN: ("defensive", 0.0, 0.0, 1.0),
}


@dataclass(frozen=True)
class RegimeInfo:
    """Static metadata for one fitted regime (state)."""

    regime_id: int
    regime_name: str
    expected_return: float        # mean of the return feature (z-score units)
    expected_volatility: float    # std of the return feature (z-score units)
    recommended_strategy_type: str
    max_leverage_allowed: float
    max_position_size_pct: float
    min_confidence_to_act: float


@dataclass(frozen=True)
class RegimeState:
    """Point-in-time regime classification for one bar."""

    label: RegimeLabel
    state_id: int
    probability: float
    state_probabilities: dict[int, float]
    timestamp: datetime | None
    is_confirmed: bool
    consecutive_bars: int
