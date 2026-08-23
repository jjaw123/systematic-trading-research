"""Position tracking: fills, P&L, reconciliation, risk-manager feed.

Subscribes to Alpaca's trade-update stream for instant fill notifications,
maintains the local position book, and pushes every equity mark into the
CircuitBreaker so drawdown control always sees actual P&L.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.broker.alpaca_client import AlpacaClient
from core.risk_manager import PortfolioState, PositionInfo, RiskManager

logger = logging.getLogger("regime_trader.positions")


@dataclass
class TrackedPosition:
    """One open position with entry context and live marks."""

    symbol: str
    qty: float
    entry_price: float
    entry_time: datetime | None
    current_price: float
    stop_level: float | None = None
    regime_at_entry: str | None = None
    current_regime: str | None = None

    @property
    def market_value(self) -> float:
        return self.qty * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.qty * (self.current_price - self.entry_price)

    @property
    def holding_days(self) -> float:
        if self.entry_time is None:
            return 0.0
        delta = datetime.now(timezone.utc) - self.entry_time
        return delta.total_seconds() / 86_400

    @property
    def regime_changed_since_entry(self) -> bool:
        return (self.regime_at_entry is not None
                and self.current_regime is not None
                and self.regime_at_entry != self.current_regime)


class PositionTracker:
    """Local position book reconciled with Alpaca, feeding the risk layer.

    Args:
        client: Connected :class:`AlpacaClient`.
        risk_manager: Receives ``update_equity`` on every fill/refresh.
        on_fill: Optional callback invoked with each fill event dict.
    """

    def __init__(self, client: AlpacaClient,
                 risk_manager: RiskManager | None = None,
                 on_fill: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.client = client
        self.risk_manager = risk_manager
        self.on_fill = on_fill
        self.positions: dict[str, TrackedPosition] = {}
        self.current_regime: str | None = None
        self.day_start_equity: float | None = None
        self.week_start_equity: float | None = None
        self.peak_equity: float = 0.0
        self.trades_today: int = 0
        self._stream: Any = None
        self._stream_thread: threading.Thread | None = None

    # ---------------------------------------------------------------- sync

    def sync(self) -> None:
        """Reconcile the local book with Alpaca (source of truth).

        Positions only known locally are dropped (with a warning); broker
        positions absent locally are adopted; quantity mismatches take the
        broker's number. Entry context survives for matching symbols.
        """
        broker_positions = {p["symbol"]: p for p in self.client.get_positions()}
        for symbol in list(self.positions):
            if symbol not in broker_positions:
                logger.warning("sync: %s tracked locally but not at broker — "
                               "dropping", symbol)
                del self.positions[symbol]
        for symbol, bp in broker_positions.items():
            local = self.positions.get(symbol)
            if local is None:
                logger.info("sync: adopting broker position %s qty=%s",
                            symbol, bp["qty"])
                self.positions[symbol] = TrackedPosition(
                    symbol=symbol, qty=bp["qty"] or 0.0,
                    entry_price=bp["avg_entry_price"] or 0.0,
                    entry_time=None,  # unknown for pre-existing positions
                    current_price=bp["current_price"]
                    or bp["avg_entry_price"] or 0.0,
                )
            else:
                if local.qty != bp["qty"]:
                    logger.warning("sync: %s qty mismatch local=%s broker=%s "
                                   "— adopting broker", symbol, local.qty,
                                   bp["qty"])
                    local.qty = bp["qty"] or 0.0
                local.entry_price = bp["avg_entry_price"] or local.entry_price
                if bp["current_price"]:
                    local.current_price = bp["current_price"]
        self.refresh_equity()

    def refresh_equity(self) -> float:
        """Pull account equity, roll anchors, and feed the circuit breaker."""
        account = self.client.get_account()
        equity = float(account["equity"] or 0.0)
        if self.day_start_equity is None:
            self.day_start_equity = self.week_start_equity = equity
        self.peak_equity = max(self.peak_equity, equity)
        if self.risk_manager is not None:
            self.risk_manager.update_equity(
                equity, regime_label=self.current_regime,
                open_positions=len(self.positions))
        return equity

    def mark_new_day(self, equity: float | None = None) -> None:
        """Roll daily anchors (call at each session open)."""
        equity = equity if equity is not None else self.refresh_equity()
        self.day_start_equity = equity
        self.trades_today = 0
        if self.risk_manager is not None:
            self.risk_manager.breaker.reset_daily(equity)

    def mark_new_week(self, equity: float | None = None) -> None:
        """Roll weekly (and daily) anchors (call at each week open)."""
        equity = equity if equity is not None else self.refresh_equity()
        self.week_start_equity = self.day_start_equity = equity
        self.trades_today = 0
        if self.risk_manager is not None:
            self.risk_manager.breaker.reset_weekly(equity)

    # ---------------------------------------------------------------- fills

    def handle_trade_update(self, update: dict[str, Any]) -> None:
        """Apply one trade-update event (fill / partial_fill / cancel).

        Expected shape (subset of Alpaca's trade_updates payload):
        {event, order: {symbol, side, filled_qty, filled_avg_price}, ...}
        """
        event = update.get("event")
        order = update.get("order") or {}
        symbol = order.get("symbol")
        if event not in ("fill", "partial_fill") or not symbol:
            logger.debug("trade update ignored: event=%s symbol=%s",
                         event, symbol)
            return
        side = str(order.get("side") or "")
        fill_qty = float(update.get("qty")
                         or order.get("filled_qty") or 0.0)
        price = float(update.get("price")
                      or order.get("filled_avg_price") or 0.0)
        signed = fill_qty if side == "buy" else -fill_qty
        pos = self.positions.get(symbol)
        now = datetime.now(timezone.utc)
        if pos is None:
            if signed > 0:
                self.positions[symbol] = TrackedPosition(
                    symbol=symbol, qty=signed, entry_price=price,
                    entry_time=now, current_price=price,
                    regime_at_entry=self.current_regime,
                    current_regime=self.current_regime,
                )
        else:
            new_qty = pos.qty + signed
            if signed > 0 and new_qty > 0:  # adding: blend entry price
                pos.entry_price = ((pos.entry_price * pos.qty
                                    + price * signed) / new_qty)
            pos.qty = new_qty
            pos.current_price = price
            if new_qty <= 0:
                logger.info("position closed %s at %.2f", symbol, price)
                del self.positions[symbol]
        if event == "fill":
            self.trades_today += 1
        logger.info("fill applied: %s %s %.0f @ %.2f (event=%s)",
                    symbol, side, fill_qty, price, event)
        self.refresh_equity()
        if self.on_fill is not None:
            self.on_fill(update)

    def update_price(self, symbol: str, price: float) -> None:
        """Mark one position to a new price."""
        pos = self.positions.get(symbol)
        if pos is not None and price > 0:
            pos.current_price = price

    def set_stop(self, symbol: str, stop: float) -> None:
        pos = self.positions.get(symbol)
        if pos is not None:
            pos.stop_level = stop

    def set_regime(self, regime_label: str | None) -> None:
        """Record the current regime (stamped onto new fills and marks)."""
        self.current_regime = regime_label
        for pos in self.positions.values():
            pos.current_regime = regime_label

    # ---------------------------------------------------------------- state

    def portfolio_state(self, flicker_rate: float = 0.0) -> PortfolioState:
        """Build the PortfolioState the risk manager validates against."""
        account = self.client.get_account()
        equity = float(account["equity"] or 0.0)
        day_start = self.day_start_equity or equity
        week_start = self.week_start_equity or equity
        self.peak_equity = max(self.peak_equity, equity)
        return PortfolioState(
            equity=equity,
            cash=float(account["cash"] or 0.0),
            buying_power=float(account["buying_power"] or 0.0),
            positions={
                s: PositionInfo(symbol=s, qty=p.qty,
                                market_value=p.market_value)
                for s, p in self.positions.items()
            },
            daily_pnl=equity - day_start,
            weekly_pnl=equity - week_start,
            peak_equity=self.peak_equity,
            trades_today=self.trades_today,
            circuit_breaker_status=(self.risk_manager.breaker.status
                                    if self.risk_manager else None),
            flicker_rate=flicker_rate,
            timestamp=datetime.now(timezone.utc),
        )

    # --------------------------------------------------------------- stream

    def start_stream(self) -> None:
        """Subscribe to trade updates over websocket (daemon thread)."""
        from alpaca.trading.stream import TradingStream  # lazy: ws dependency

        stream = TradingStream(self.client.api_key, self.client.secret_key,
                               paper=self.client.paper)

        async def _handler(data: Any) -> None:
            try:
                payload = data if isinstance(data, dict) else {
                    "event": str(getattr(data, "event", "")),
                    "qty": getattr(data, "qty", None),
                    "price": getattr(data, "price", None),
                    "order": {
                        "symbol": getattr(data.order, "symbol", None),
                        "side": str(getattr(
                            getattr(data.order, "side", None), "value",
                            getattr(data.order, "side", ""))),
                        "filled_qty": getattr(data.order, "filled_qty", None),
                        "filled_avg_price": getattr(
                            data.order, "filled_avg_price", None),
                    } if getattr(data, "order", None) else {},
                }
                self.handle_trade_update(payload)
            except Exception:
                logger.exception("trade update handling failed")

        stream.subscribe_trade_updates(_handler)
        self._stream = stream
        self._stream_thread = threading.Thread(target=stream.run,
                                               name="trade-updates",
                                               daemon=True)
        self._stream_thread.start()
        logger.info("trade-update stream started")

    def stop_stream(self) -> None:
        """Stop the trade-update stream cleanly."""
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                logger.exception("stream stop failed")
            self._stream = None
            logger.info("trade-update stream stopped")
