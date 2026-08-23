"""Order execution: limit-first placement, brackets, stop management.

Every execution carries a unique ``trade_id`` linking
signal -> risk decision -> order(s) -> fills for end-to-end audit.

Default behavior: LIMIT orders at +/- 0.1% of the reference price, canceled
after 30s if unfilled, optionally retried at market for the remainder.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from core.broker.alpaca_client import AlpacaClient
from core.regime_strategies import Direction, Signal
from core.risk_manager import RiskDecision

logger = logging.getLogger("regime_trader.executor")

TERMINAL_STATUSES = {"filled", "canceled", "expired", "rejected",
                     "done_for_day"}


@dataclass
class OrderRecord:
    """Audit record for one execution attempt (and its retries)."""

    trade_id: str
    symbol: str
    side: str
    qty: float
    order_id: str
    status: str
    limit_price: float | None
    submitted_at: datetime
    filled_qty: float = 0.0
    avg_fill_price: float | None = None
    signal: Signal | None = None
    risk_decision: RiskDecision | None = None
    child_order_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def remaining_qty(self) -> float:
        return max(0.0, self.qty - self.filled_qty)


class OrderExecutor:
    """Places, monitors, modifies, and cancels orders through Alpaca.

    Args:
        client: Connected :class:`AlpacaClient`.
        limit_offset_pct: Limit price offset from reference (0.001 = 0.1%).
        fill_timeout: Seconds to wait for a limit fill before canceling.
        poll_interval: Seconds between order-status polls.
        clock, sleep: Injectable time sources for tests.
    """

    def __init__(self, client: AlpacaClient,
                 limit_offset_pct: float = 0.001,
                 fill_timeout: float = 30.0,
                 poll_interval: float = 1.0,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.client = client
        self.limit_offset_pct = limit_offset_pct
        self.fill_timeout = fill_timeout
        self.poll_interval = poll_interval
        self._clock = clock
        self._sleep = sleep
        self.records: dict[str, OrderRecord] = {}

    # ------------------------------------------------------------ placement

    def submit_order(self, signal: Signal, qty: int,
                     risk_decision: RiskDecision | None = None,
                     retry_market: bool = True) -> OrderRecord:
        """Place a LIMIT order for a signal; cancel after the timeout and
        optionally chase the remainder at market.

        Args:
            signal: Risk-approved signal (entry_price is the reference).
            qty: Share quantity (risk-approved).
            risk_decision: Linked into the audit record.
            retry_market: Chase unfilled remainder with a market order.
        """
        if qty <= 0:
            raise ValueError("qty must be positive")
        side = OrderSide.BUY if signal.direction is Direction.LONG else OrderSide.SELL
        offset = 1 + self.limit_offset_pct if side is OrderSide.BUY \
            else 1 - self.limit_offset_pct
        limit_price = round(signal.entry_price * offset, 2)
        trade_id = f"rt-{uuid.uuid4().hex[:12]}"
        request = LimitOrderRequest(
            symbol=signal.symbol, qty=qty, side=side,
            time_in_force=TimeInForce.DAY, limit_price=limit_price,
            client_order_id=trade_id,
        )
        response = self.client.submit_order(request)
        record = OrderRecord(
            trade_id=trade_id, symbol=signal.symbol, side=side.value,
            qty=float(qty), order_id=response["id"],
            status=response["status"], limit_price=limit_price,
            submitted_at=datetime.now(timezone.utc),
            signal=signal, risk_decision=risk_decision,
        )
        self.records[trade_id] = record
        logger.info("order submitted trade_id=%s %s %d %s limit=%.2f",
                    trade_id, side.value, qty, signal.symbol, limit_price)

        if not self._await_fill(record):
            self._cancel_and_maybe_chase(record, retry_market)
        return record

    def submit_bracket_order(self, signal: Signal, qty: int,
                             risk_decision: RiskDecision | None = None
                             ) -> OrderRecord:
        """Place entry + stop-loss + take-profit as one bracket (OCO legs).

        The take-profit defaults to 2R (entry + 2x the stop distance) when
        the signal doesn't specify one — Alpaca brackets require both legs.
        """
        if qty <= 0:
            raise ValueError("qty must be positive")
        if signal.stop_loss is None:
            raise ValueError("bracket order requires a stop loss")
        side = OrderSide.BUY if signal.direction is Direction.LONG else OrderSide.SELL
        offset = 1 + self.limit_offset_pct if side is OrderSide.BUY \
            else 1 - self.limit_offset_pct
        limit_price = round(signal.entry_price * offset, 2)
        take_profit = signal.take_profit
        if take_profit is None:
            take_profit = signal.entry_price + 2 * (signal.entry_price
                                                    - signal.stop_loss)
        trade_id = f"rt-{uuid.uuid4().hex[:12]}"
        request = LimitOrderRequest(
            symbol=signal.symbol, qty=qty, side=side,
            time_in_force=TimeInForce.GTC, limit_price=limit_price,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=round(take_profit, 2)),
            stop_loss=StopLossRequest(stop_price=round(signal.stop_loss, 2)),
            client_order_id=trade_id,
        )
        response = self.client.submit_order(request)
        record = OrderRecord(
            trade_id=trade_id, symbol=signal.symbol, side=side.value,
            qty=float(qty), order_id=response["id"],
            status=response["status"], limit_price=limit_price,
            submitted_at=datetime.now(timezone.utc),
            signal=signal, risk_decision=risk_decision,
            child_order_ids=[leg["id"] for leg in response.get("legs", [])],
        )
        record.notes.append(f"bracket stop={signal.stop_loss:.2f} "
                            f"tp={take_profit:.2f}")
        self.records[trade_id] = record
        logger.info("bracket submitted trade_id=%s %s %d %s stop=%.2f tp=%.2f",
                    trade_id, side.value, qty, signal.symbol,
                    signal.stop_loss, take_profit)
        return record

    # ----------------------------------------------------------- management

    def modify_stop(self, symbol: str, new_stop: float) -> dict[str, Any] | None:
        """Tighten (raise) the stop on a long position — never widen.

        Returns the replaced order dict, or None when no stop exists or the
        request would widen the stop.
        """
        stops = [o for o in self.client.list_orders("open")
                 if o["symbol"] == symbol and o.get("stop_price")]
        if not stops:
            logger.warning("modify_stop %s: no open stop order found", symbol)
            return None
        order = stops[0]
        current = float(order["stop_price"])
        if new_stop <= current:
            logger.warning("modify_stop %s: refusing to widen stop "
                           "%.2f -> %.2f", symbol, current, new_stop)
            return None
        replaced = self.client.replace_order(order["id"], stop_price=new_stop)
        logger.info("stop tightened %s: %.2f -> %.2f", symbol, current,
                    new_stop)
        return replaced

    def cancel_order(self, trade_id: str) -> None:
        """Cancel the working order for a trade id."""
        record = self.records[trade_id]
        self.client.cancel_order(record.order_id)
        record.status = "canceled"
        record.notes.append("canceled by request")
        logger.info("order canceled trade_id=%s", trade_id)

    def close_position(self, symbol: str) -> dict[str, Any]:
        """Close one position at market."""
        logger.info("closing position %s", symbol)
        return self.client.close_position(symbol)

    def close_all_positions(self) -> list[dict[str, Any]]:
        """Flatten everything and cancel all open orders (halt path)."""
        logger.warning("closing ALL positions and canceling open orders")
        return self.client.close_all_positions()

    def get_record(self, trade_id: str) -> OrderRecord | None:
        return self.records.get(trade_id)

    # ------------------------------------------------------------ internals

    def _await_fill(self, record: OrderRecord) -> bool:
        """Poll until filled or the timeout elapses. Returns filled?"""
        deadline = self._clock() + self.fill_timeout
        while True:
            state = self.client.get_order(record.order_id)
            record.status = state["status"]
            record.filled_qty = state["filled_qty"] or 0.0
            record.avg_fill_price = state["filled_avg_price"]
            if record.status == "filled":
                logger.info("filled trade_id=%s qty=%.0f avg=%.2f",
                            record.trade_id, record.filled_qty,
                            record.avg_fill_price or 0.0)
                return True
            if record.status in TERMINAL_STATUSES:
                return False
            if self._clock() >= deadline:
                return False
            self._sleep(self.poll_interval)

    def _cancel_and_maybe_chase(self, record: OrderRecord,
                                retry_market: bool) -> None:
        """Cancel a stale limit order; optionally chase remainder at market."""
        if record.status not in TERMINAL_STATUSES:
            try:
                self.client.cancel_order(record.order_id)
                record.status = "canceled"
                record.notes.append(
                    f"unfilled after {self.fill_timeout:.0f}s: canceled")
                logger.warning("limit unfilled after %.0fs trade_id=%s "
                               "(filled %.0f/%.0f) — canceled",
                               self.fill_timeout, record.trade_id,
                               record.filled_qty, record.qty)
            except Exception:
                logger.exception("cancel failed trade_id=%s", record.trade_id)
                return
        remaining = int(record.remaining_qty)
        if retry_market and remaining > 0:
            request = MarketOrderRequest(
                symbol=record.symbol, qty=remaining,
                side=OrderSide(record.side), time_in_force=TimeInForce.DAY,
                client_order_id=f"{record.trade_id}-mkt",
            )
            response = self.client.submit_order(request)
            record.child_order_ids.append(response["id"])
            record.notes.append(f"market retry for {remaining} shares")
            logger.info("market retry trade_id=%s qty=%d order=%s",
                        record.trade_id, remaining, response["id"])
