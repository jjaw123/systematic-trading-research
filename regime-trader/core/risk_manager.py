"""Risk management layer: sizing, limits, circuit breakers — absolute veto.

Operates INDEPENDENTLY of the HMM: breakers fire on actual P&L, so a wrong
regime model cannot bypass drawdown control (defense in depth). Every signal
passes :meth:`RiskManager.validate_signal`; nothing reaches the broker
without its approval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from core.hmm_engine import RegimeInfo
from core.regime_strategies import Direction, Signal

logger = logging.getLogger("regime_trader.risk")


class TradingStatus(Enum):
    """Escalating risk posture. Escalates intraday, never relaxes until the
    corresponding reset boundary (new day / new week / manual lock removal)."""

    NORMAL = "normal"
    REDUCED = "reduced"     # sizes halved
    HALTED = "halted"       # no new positions
    STOPPED = "stopped"     # max drawdown from peak; manual intervention

    @property
    def severity(self) -> int:
        return _SEVERITY[self]


_SEVERITY = {TradingStatus.NORMAL: 0, TradingStatus.REDUCED: 1,
             TradingStatus.HALTED: 2, TradingStatus.STOPPED: 3}


@dataclass(frozen=True)
class RiskConfig:
    """All risk thresholds (mirrors the ``risk`` settings section)."""

    max_risk_per_trade: float = 0.01
    max_exposure: float = 0.80
    max_leverage: float = 1.25
    max_single_position: float = 0.15
    max_sector_exposure: float = 0.30
    max_concurrent: int = 5
    max_daily_trades: int = 20
    daily_dd_reduce: float = 0.02
    daily_dd_halt: float = 0.03
    weekly_dd_reduce: float = 0.05
    weekly_dd_halt: float = 0.07
    max_dd_from_peak: float = 0.10
    min_position_value: float = 100.0
    gap_stop_multiple: float = 3.0    # overnight gap assumed 3x through stop
    gap_max_loss: float = 0.02        # gap-through loss capped at 2% of equity
    max_spread_pct: float = 0.005
    duplicate_window_seconds: float = 60.0
    correlation_window: int = 60
    correlation_reduce: float = 0.70
    correlation_reject: float = 0.85
    reduced_size_mult: float = 0.50
    leverage_max_positions: int = 3   # 3+ open positions force 1.0x
    leverage_flicker_threshold: float = 4.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RiskConfig":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class PositionInfo:
    """Minimal open-position view the risk manager needs."""

    symbol: str
    qty: float
    market_value: float
    sector: str | None = None


@dataclass
class PortfolioState:
    """Portfolio snapshot supplied by the caller for each validation."""

    equity: float
    cash: float
    buying_power: float
    positions: dict[str, PositionInfo] = field(default_factory=dict)
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    peak_equity: float = 0.0
    trades_today: int = 0
    circuit_breaker_status: TradingStatus | None = None
    flicker_rate: float = 0.0
    timestamp: datetime | None = None

    @property
    def gross_value(self) -> float:
        return sum(abs(p.market_value) for p in self.positions.values())

    @property
    def gross_exposure(self) -> float:
        return self.gross_value / self.equity if self.equity > 0 else 0.0

    @property
    def drawdown_from_peak(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, 1.0 - self.equity / self.peak_equity)

    def sector_value(self, sector: str,
                     sector_map: dict[str, str] | None = None) -> float:
        total = 0.0
        for p in self.positions.values():
            s = p.sector or (sector_map or {}).get(p.symbol)
            if s == sector:
                total += abs(p.market_value)
        return total


@dataclass(frozen=True)
class BreakerEvent:
    """One circuit-breaker trigger, kept for audit."""

    timestamp: datetime
    breaker_type: str          # daily_reduce/daily_halt/weekly_reduce/...
    drawdown: float
    equity: float
    positions_closed: int
    regime_label: str | None   # what the HMM believed — tracks model misses


@dataclass
class RiskDecision:
    """Outcome of validating one signal."""

    approved: bool
    modified_signal: Signal | None
    rejection_reason: str | None
    modifications: list[str] = field(default_factory=list)
    approved_qty: int = 0
    approved_value: float = 0.0


class CircuitBreaker:
    """P&L-based drawdown breakers, independent of the regime model.

    Levels only escalate within their period (``reset_daily``/``reset_weekly``
    roll the anchors); the peak-drawdown stop writes ``trading_halted.lock``
    and trading resumes only after the file is manually deleted.
    """

    def __init__(self, config: RiskConfig, lock_file: Path) -> None:
        self.config = config
        self.lock_file = Path(lock_file)
        self.day_start: float | None = None
        self.week_start: float | None = None
        self.peak: float | None = None
        self._daily_level = 0     # 0 none, 1 reduce, 2 halt
        self._weekly_level = 0
        self._stopped = False
        self._history: list[BreakerEvent] = []
        if self.lock_file.exists():
            self._stopped = True
            logger.critical("halt lock file present at startup (%s) — trading "
                            "STOPPED until it is manually deleted",
                            self.lock_file)

    @property
    def status(self) -> TradingStatus:
        if self._stopped:
            return TradingStatus.STOPPED
        if max(self._daily_level, self._weekly_level) >= 2:
            return TradingStatus.HALTED
        if max(self._daily_level, self._weekly_level) >= 1:
            return TradingStatus.REDUCED
        return TradingStatus.NORMAL

    @property
    def size_multiplier(self) -> float:
        return {TradingStatus.NORMAL: 1.0,
                TradingStatus.REDUCED: self.config.reduced_size_mult,
                TradingStatus.HALTED: 0.0,
                TradingStatus.STOPPED: 0.0}[self.status]

    def check(self) -> TradingStatus:
        """Re-evaluate the lock file and return the current status."""
        if self._stopped and not self.lock_file.exists():
            self._resume()
        return self.status

    def update(self, equity: float, regime_label: str | None = None,
               open_positions: int = 0,
               timestamp: datetime | None = None) -> TradingStatus:
        """Feed the latest equity mark; escalates breaker levels on breach."""
        ts = timestamp or datetime.now(timezone.utc)
        if self.day_start is None:
            self.day_start = self.week_start = self.peak = equity
        if self._stopped:
            if not self.lock_file.exists():
                self._resume(equity)
            else:
                return self.status
        self.peak = max(self.peak, equity)
        daily_dd = max(0.0, 1.0 - equity / self.day_start)
        weekly_dd = max(0.0, 1.0 - equity / self.week_start)
        peak_dd = max(0.0, 1.0 - equity / self.peak)
        cfg = self.config

        if peak_dd > cfg.max_dd_from_peak:
            self._stopped = True
            self.lock_file.write_text(
                f"trading halted {ts.isoformat()}: drawdown from peak "
                f"{peak_dd:.2%} exceeded {cfg.max_dd_from_peak:.0%}. Delete "
                "this file to resume trading.\n"
            )
            self._fire("peak_stop", peak_dd, equity, open_positions,
                       regime_label, ts, critical=True)
            return self.status

        new_daily = 2 if daily_dd > cfg.daily_dd_halt else \
            1 if daily_dd > cfg.daily_dd_reduce else 0
        if new_daily > self._daily_level:
            self._daily_level = new_daily
            self._fire("daily_halt" if new_daily == 2 else "daily_reduce",
                       daily_dd, equity, open_positions, regime_label, ts)

        new_weekly = 2 if weekly_dd > cfg.weekly_dd_halt else \
            1 if weekly_dd > cfg.weekly_dd_reduce else 0
        if new_weekly > self._weekly_level:
            self._weekly_level = new_weekly
            self._fire("weekly_halt" if new_weekly == 2 else "weekly_reduce",
                       weekly_dd, equity, open_positions, regime_label, ts)
        return self.status

    def reset_daily(self, equity: float) -> None:
        """Roll the daily anchor at the session boundary."""
        self.day_start = equity
        self._daily_level = 0

    def reset_weekly(self, equity: float) -> None:
        """Roll the weekly (and daily) anchors at the week boundary."""
        self.week_start = self.day_start = equity
        self._daily_level = self._weekly_level = 0

    def get_history(self) -> list[BreakerEvent]:
        return list(self._history)

    def _resume(self, equity: float | None = None) -> None:
        logger.warning("halt lock file removed — resuming trading with a "
                       "fresh risk budget")
        self._stopped = False
        self._daily_level = self._weekly_level = 0
        if equity is not None:
            self.day_start = self.week_start = self.peak = equity
        else:
            self.day_start = self.week_start = self.peak = None

    def _fire(self, breaker_type: str, dd: float, equity: float,
              positions: int, regime: str | None, ts: datetime,
              critical: bool = False) -> None:
        self._history.append(BreakerEvent(ts, breaker_type, dd, equity,
                                          positions, regime))
        log = logger.critical if critical else logger.warning
        log("CIRCUIT BREAKER %s: drawdown=%.2f%% equity=%.0f "
            "open_positions=%d hmm_regime=%s",
            breaker_type, dd * 100, equity, positions, regime or "n/a")


class RiskManager:
    """Validates and sizes every signal; absolute veto over the strategy.

    Args:
        config: RiskConfig or the ``risk`` settings dict.
        lock_file: Path of the manual-intervention halt lock.
    """

    def __init__(self, config: RiskConfig | dict[str, Any] | None = None,
                 lock_file: str | Path = "trading_halted.lock") -> None:
        if isinstance(config, dict):
            self.config = RiskConfig.from_dict(config)
        else:
            self.config = config or RiskConfig()
        self.breaker = CircuitBreaker(self.config, Path(lock_file))
        self._recent_orders: dict[tuple[str, str], datetime] = {}

    # ------------------------------------------------------------- breakers

    def update_equity(self, equity: float, regime_label: str | None = None,
                      open_positions: int = 0,
                      timestamp: datetime | None = None) -> TradingStatus:
        """Feed the latest equity into the circuit breakers."""
        return self.breaker.update(equity, regime_label, open_positions,
                                   timestamp)

    def position_size(self, equity: float, entry: float, stop: float) -> int:
        """Risk-based size: (equity * max_risk_per_trade) / |entry - stop|."""
        dist = entry - stop
        if dist <= 0 or entry <= 0:
            return 0
        return int(equity * self.config.max_risk_per_trade / dist)

    # ------------------------------------------------------------ validation

    def validate_signal(
        self,
        signal: Signal,
        state: PortfolioState,
        *,
        regime_info: RegimeInfo | None = None,
        price_history: pd.DataFrame | None = None,
        quote: dict[str, Any] | None = None,
        sector_map: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> RiskDecision:
        """Run the full veto pipeline; returns an approved (possibly resized)
        signal or a structured rejection.

        Optional inputs: ``regime_info`` (per-regime cap and confidence
        floor), ``price_history`` (closes per symbol, for correlation),
        ``quote`` ({bid, ask, tradable}), ``sector_map``, ``now`` (clock
        injection for the duplicate-order window).
        """
        cfg = self.config
        mods: list[str] = []
        now = now or signal.timestamp or datetime.now(timezone.utc)

        # Closing/flattening is always allowed — risk reduction never blocked.
        if signal.direction is Direction.FLAT:
            return RiskDecision(True, signal, None, ["close-only signal"])

        status = self.breaker.check()
        if (state.circuit_breaker_status is not None
                and state.circuit_breaker_status.severity > status.severity):
            status = state.circuit_breaker_status
        if status in (TradingStatus.HALTED, TradingStatus.STOPPED):
            return self._reject(signal, f"circuit breaker {status.value}")

        # -- mandatory stop loss ------------------------------------------
        if signal.stop_loss is None:
            return self._reject(signal, "missing stop loss — every position "
                                        "must have one")
        entry, stop = float(signal.entry_price), float(signal.stop_loss)
        if entry <= 0:
            return self._reject(signal, "invalid entry price")
        dist = entry - stop
        if dist <= 0:
            return self._reject(signal, "stop loss not below entry")

        # -- trade-count / concurrency / duplicates -----------------------
        if state.trades_today >= cfg.max_daily_trades:
            return self._reject(signal, f"daily trade limit "
                                        f"({cfg.max_daily_trades}) reached")
        if (signal.symbol not in state.positions
                and len(state.positions) >= cfg.max_concurrent):
            return self._reject(signal, f"max concurrent positions "
                                        f"({cfg.max_concurrent}) reached")
        key = (signal.symbol, signal.direction.value)
        last = self._recent_orders.get(key)
        if last is not None and (now - last).total_seconds() < cfg.duplicate_window_seconds:
            return self._reject(signal, "duplicate order within "
                                        f"{cfg.duplicate_window_seconds:.0f}s")

        # -- market quality -----------------------------------------------
        if quote is not None:
            if quote.get("tradable") is False:
                return self._reject(signal, "symbol not tradable")
            bid, ask = quote.get("bid"), quote.get("ask")
            if bid and ask and bid > 0:
                spread = (ask - bid) / ((ask + bid) / 2)
                if spread > cfg.max_spread_pct:
                    return self._reject(
                        signal, f"spread {spread:.2%} exceeds "
                                f"{cfg.max_spread_pct:.2%}")

        # -- risk-based sizing and the cap chain --------------------------
        equity = state.equity
        qty = self.position_size(equity, entry, stop)
        if qty <= 0:
            return self._reject(signal, "risk sizing produced zero quantity")

        def cap_value(limit: float, label: str) -> None:
            nonlocal qty
            capped = int(limit / entry)
            if capped < qty:
                qty = capped
                mods.append(label)

        if regime_info is not None:
            cap_value(regime_info.max_position_size_pct * equity,
                      f"regime cap {regime_info.max_position_size_pct:.0%}")
        cap_value(cfg.max_single_position * equity,
                  f"single-position cap {cfg.max_single_position:.0%}")

        headroom = cfg.max_exposure * equity - state.gross_value
        if headroom <= 0:
            return self._reject(signal, f"max exposure "
                                        f"({cfg.max_exposure:.0%}) reached")
        cap_value(headroom, "exposure headroom cap")

        sector = (sector_map or {}).get(signal.symbol)
        if sector is not None:
            sector_headroom = (cfg.max_sector_exposure * equity
                               - state.sector_value(sector, sector_map))
            if sector_headroom <= 0:
                return self._reject(signal, f"sector '{sector}' at max "
                                            f"exposure ({cfg.max_sector_exposure:.0%})")
            cap_value(sector_headroom, f"sector cap ({sector})")

        # Overnight gap risk: assume price gaps gap_stop_multiple x through
        # the stop; that loss must stay within gap_max_loss of equity.
        gap_qty = int(cfg.gap_max_loss * equity / (cfg.gap_stop_multiple * dist))
        if gap_qty < qty:
            qty = gap_qty
            mods.append("overnight gap-risk cap")

        # -- correlation with existing positions --------------------------
        max_corr = self._max_correlation(signal.symbol, state, price_history)
        if max_corr is not None:
            if max_corr > cfg.correlation_reject:
                return self._reject(signal, f"correlation {max_corr:.2f} with "
                                            "held position exceeds "
                                            f"{cfg.correlation_reject}")
            if max_corr > cfg.correlation_reduce:
                qty = int(qty * 0.5)
                mods.append(f"correlation {max_corr:.2f} > "
                            f"{cfg.correlation_reduce}: size halved")

        # -- breaker size reduction ---------------------------------------
        if status is TradingStatus.REDUCED:
            qty = int(qty * cfg.reduced_size_mult)
            mods.append("circuit breaker REDUCED: size halved")

        # -- buying power and minimum size --------------------------------
        if qty * entry > state.buying_power:
            qty = int(state.buying_power / entry)
            mods.append("clipped to buying power")
        value = qty * entry
        if value < cfg.min_position_value:
            return self._reject(signal, f"position value {value:.0f} below "
                                        f"minimum ${cfg.min_position_value:.0f}")

        # -- leverage rules ------------------------------------------------
        leverage = min(signal.leverage, cfg.max_leverage)
        force_1x = []
        if status is not TradingStatus.NORMAL:
            force_1x.append("circuit breaker active")
        if len(state.positions) >= cfg.leverage_max_positions:
            force_1x.append(f"{len(state.positions)} positions open")
        if state.flicker_rate > cfg.leverage_flicker_threshold:
            force_1x.append("high regime flicker")
        if signal.metadata.get("uncertainty_mode"):
            force_1x.append("regime uncertain")
        if (regime_info is not None
                and signal.regime_probability < regime_info.min_confidence_to_act):
            force_1x.append("confidence below regime floor")
        if force_1x and leverage > 1.0:
            leverage = 1.0
            mods.append("leverage forced to 1.0x: " + "; ".join(force_1x))

        self._recent_orders[key] = now
        modified = replace(
            signal, leverage=leverage, position_size_pct=value / equity,
            metadata={**signal.metadata, "approved_qty": qty,
                      "risk_modifications": mods},
        )
        if mods:
            logger.info("signal approved with modifications symbol=%s qty=%d "
                        "value=%.0f mods=%s", signal.symbol, qty, value, mods)
        return RiskDecision(True, modified, None, mods, qty, value)

    # ------------------------------------------------------------- helpers

    def _max_correlation(self, symbol: str, state: PortfolioState,
                         price_history: pd.DataFrame | None) -> float | None:
        """Highest 60-day return correlation with any held position."""
        if price_history is None or symbol not in price_history.columns:
            return None
        rets = price_history.pct_change().tail(self.config.correlation_window)
        cand = rets[symbol]
        corrs = [cand.corr(rets[s]) for s in state.positions
                 if s != symbol and s in rets.columns]
        corrs = [c for c in corrs if pd.notna(c)]
        return max(corrs) if corrs else None

    def _reject(self, signal: Signal, reason: str) -> RiskDecision:
        logger.warning("signal REJECTED symbol=%s direction=%s reason=%s",
                       signal.symbol, signal.direction.value, reason)
        return RiskDecision(False, None, reason, [])
