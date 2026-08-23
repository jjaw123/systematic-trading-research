"""Alpaca API wrapper (alpaca-py SDK).

Centralizes authentication, paper/live endpoint selection, retry with
exponential backoff, and plain-dict conversion of SDK models so the rest of
the codebase never touches alpaca-py types directly.

Credentials come from the environment (.env, gitignored) — never hardcoded.
Paper trading is the default; live trading requires an explicit typed
confirmation at startup.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any

from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest, ReplaceOrderRequest

logger = logging.getLogger("regime_trader.broker")

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"
LIVE_CONFIRMATION = "YES I UNDERSTAND THE RISKS"


def _f(value: Any) -> float | None:
    """Float conversion tolerant of None/'' from the API."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _enum_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


class AlpacaClient:
    """Authenticated Alpaca trading + market data client with retry.

    Args:
        api_key: Alpaca API key (from ALPACA_API_KEY).
        secret_key: Alpaca secret key (from ALPACA_SECRET_KEY).
        paper: Use the paper endpoint (default True — live is opt-in only).
        max_retries: Attempts per call before giving up.
        backoff_base: First retry delay in seconds (doubles per attempt).
        sleep: Injectable sleep for tests.
    """

    def __init__(self, api_key: str, secret_key: str, paper: bool = True,
                 max_retries: int = 5, backoff_base: float = 1.0,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if not api_key or not secret_key:
            raise ValueError("Alpaca credentials are required")
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._sleep = sleep
        self._trading: TradingClient | None = None
        self._data: StockHistoricalDataClient | None = None

    # ------------------------------------------------------------ lifecycle

    @classmethod
    def from_env(cls, paper: bool | None = None,
                 input_fn: Callable[[str], str] = input,
                 **kwargs: Any) -> "AlpacaClient":
        """Build a client from ALPACA_API_KEY / ALPACA_SECRET_KEY /
        ALPACA_PAPER. Live mode demands a typed confirmation.

        Raises:
            ValueError: If credentials are missing.
            RuntimeError: If live mode is not explicitly confirmed.
        """
        api_key = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        if not api_key or not secret_key:
            raise ValueError("ALPACA_API_KEY / ALPACA_SECRET_KEY not set — "
                             "copy .env.example to .env and fill them in")
        if paper is None:
            paper = os.environ.get("ALPACA_PAPER", "true").strip().lower() != "false"
        if not paper:
            answer = input_fn("⚠️ LIVE TRADING MODE. Type "
                              f"'{LIVE_CONFIRMATION}' to confirm: ")
            if answer.strip() != LIVE_CONFIRMATION:
                raise RuntimeError("live trading not confirmed — aborting")
            logger.critical("LIVE trading mode confirmed (%s)", LIVE_URL)
        return cls(api_key, secret_key, paper=paper, **kwargs)

    def connect(self) -> dict[str, Any]:
        """Instantiate the SDK clients and run the startup health check."""
        self._make_clients()
        return self.health_check()

    def _make_clients(self) -> None:
        self._trading = TradingClient(self.api_key, self.secret_key,
                                      paper=self.paper)
        self._data = StockHistoricalDataClient(self.api_key, self.secret_key)
        logger.info("Alpaca clients created (%s)",
                    PAPER_URL if self.paper else LIVE_URL)

    def health_check(self) -> dict[str, Any]:
        """Verify connectivity and account status; returns the account."""
        account = self.get_account()
        logger.info("Alpaca health check: status=%s equity=%s paper=%s",
                    account.get("status"), account.get("equity"), self.paper)
        if account.get("status") != "ACTIVE":
            logger.warning("account status is %s (not ACTIVE)",
                           account.get("status"))
        return account

    @property
    def trading(self) -> TradingClient:
        if self._trading is None:
            raise RuntimeError("not connected — call connect() first")
        return self._trading

    @property
    def data(self) -> StockHistoricalDataClient:
        if self._data is None:
            raise RuntimeError("not connected — call connect() first")
        return self._data

    def _call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run an SDK call with exponential-backoff retry and reconnect.

        Client errors (4xx/auth) raise immediately; transient failures
        back off (1s, 2s, 4s, ...) and rebuild the clients.
        """
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except APIError as exc:
                code = getattr(exc, "status_code", None)
                if code is not None and 400 <= int(code) < 500:
                    raise  # our mistake or auth problem — retrying won't help
                last_exc = exc
            except Exception as exc:  # network / websocket / timeout
                last_exc = exc
            delay = self.backoff_base * (2 ** attempt)
            logger.warning("Alpaca call failed (%s); retry %d/%d in %.0fs",
                           last_exc, attempt + 1, self.max_retries, delay)
            self._sleep(delay)
            try:
                self._make_clients()
            except Exception:  # keep retrying on reconnect failure
                logger.exception("reconnect failed")
        raise ConnectionError(
            f"Alpaca call failed after {self.max_retries} retries"
        ) from last_exc

    # -------------------------------------------------------------- account

    def get_account(self) -> dict[str, Any]:
        """Account snapshot: equity, cash, buying power, status, flags."""
        a = self._call(self.trading.get_account)
        return {
            "id": str(a.id), "status": _enum_str(a.status),
            "equity": _f(a.equity), "cash": _f(a.cash),
            "buying_power": _f(a.buying_power),
            "regt_buying_power": _f(a.regt_buying_power),
            "daytrading_buying_power": _f(a.daytrading_buying_power),
            "portfolio_value": _f(a.portfolio_value),
            "pattern_day_trader": bool(a.pattern_day_trader),
            "trading_blocked": bool(a.trading_blocked),
            "currency": str(a.currency),
        }

    def get_positions(self) -> list[dict[str, Any]]:
        """All open positions as plain dicts."""
        out = []
        for p in self._call(self.trading.get_all_positions):
            out.append({
                "symbol": p.symbol, "qty": _f(p.qty),
                "avg_entry_price": _f(p.avg_entry_price),
                "current_price": _f(p.current_price),
                "market_value": _f(p.market_value),
                "unrealized_pl": _f(p.unrealized_pl),
                "side": _enum_str(p.side),
            })
        return out

    def get_order_history(self, limit: int = 100,
                          status: str = "closed") -> list[dict[str, Any]]:
        """Recent orders ('open', 'closed', or 'all')."""
        req = GetOrdersRequest(status=QueryOrderStatus(status), limit=limit)
        orders = self._call(self.trading.get_orders, filter=req)
        return [self._order_to_dict(o) for o in orders]

    def get_clock(self) -> dict[str, Any]:
        """Market clock: is_open, next_open, next_close, timestamp."""
        c = self._call(self.trading.get_clock)
        return {"is_open": bool(c.is_open), "next_open": c.next_open,
                "next_close": c.next_close, "timestamp": c.timestamp}

    def is_market_open(self) -> bool:
        return self.get_clock()["is_open"]

    def get_available_margin(self) -> float:
        """Reg-T buying power (falls back to plain buying power)."""
        account = self.get_account()
        margin = account.get("regt_buying_power") or account.get("buying_power")
        return float(margin or 0.0)

    # --------------------------------------------------------------- orders

    def submit_order(self, order_request: Any) -> dict[str, Any]:
        """Submit an alpaca-py order request; returns the order as a dict."""
        o = self._call(self.trading.submit_order, order_data=order_request)
        return self._order_to_dict(o)

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._order_to_dict(
            self._call(self.trading.get_order_by_id, order_id))

    def cancel_order(self, order_id: str) -> None:
        self._call(self.trading.cancel_order_by_id, order_id)

    def replace_order(self, order_id: str, *, qty: int | None = None,
                      limit_price: float | None = None,
                      stop_price: float | None = None) -> dict[str, Any]:
        req = ReplaceOrderRequest(qty=qty, limit_price=limit_price,
                                  stop_price=stop_price)
        o = self._call(self.trading.replace_order_by_id, order_id,
                       order_data=req)
        return self._order_to_dict(o)

    def list_orders(self, status: str = "open",
                    limit: int = 200) -> list[dict[str, Any]]:
        req = GetOrdersRequest(status=QueryOrderStatus(status), limit=limit)
        return [self._order_to_dict(o)
                for o in self._call(self.trading.get_orders, filter=req)]

    def close_position(self, symbol: str) -> dict[str, Any]:
        """Close one position at market."""
        return self._order_to_dict(
            self._call(self.trading.close_position, symbol))

    def close_all_positions(self) -> list[dict[str, Any]]:
        """Close every position and cancel all open orders."""
        responses = self._call(self.trading.close_all_positions,
                               cancel_orders=True)
        logger.warning("close_all_positions: %d close responses",
                       len(responses or []))
        return [{"symbol": getattr(r, "symbol", None),
                 "status": _enum_str(getattr(r, "status", None))}
                for r in (responses or [])]

    @staticmethod
    def _order_to_dict(o: Any) -> dict[str, Any]:
        return {
            "id": str(o.id), "client_order_id": o.client_order_id,
            "symbol": o.symbol, "qty": _f(o.qty),
            "side": _enum_str(o.side), "type": _enum_str(o.order_type),
            "status": _enum_str(o.status),
            "limit_price": _f(o.limit_price), "stop_price": _f(o.stop_price),
            "filled_qty": _f(o.filled_qty) or 0.0,
            "filled_avg_price": _f(o.filled_avg_price),
            "submitted_at": o.submitted_at,
            "legs": [AlpacaClient._order_to_dict(leg) for leg in (o.legs or [])]
            if getattr(o, "legs", None) else [],
        }
