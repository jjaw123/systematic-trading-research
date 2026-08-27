"""Alpaca paper-trading adapter.

`assert_paper` runs at construction AND before every order submission, so a
mid-session credential or endpoint change cannot slip an order to a live
account. There is no live-trading code path in this module at all.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from . import journal
from .config import (
    MARKET_CACHE,
    PAPER_BASE_URL,
    assert_paper,
    load_credentials,
)


EXCHANGE_TZ = ZoneInfo("America/New_York")


def trading_day():
    """Today's date in EXCHANGE time.

    The UTC date rolls over at 20:00 ET, so a UTC date would put an evening
    run on the wrong side of the session boundary. Every "today" in the live
    layer means the exchange's day, not the machine's.
    """
    return datetime.now(EXCHANGE_TZ).date()


class PaperBroker:
    def __init__(self, env_path=None):
        key, secret, paper_flag = load_credentials(env_path)
        self._key, self._paper_flag = key, paper_flag
        self.base_url = PAPER_BASE_URL
        assert_paper(key, paper_flag, self.base_url)          # pre-connect
        self.trading = TradingClient(key, secret, paper=True)
        self.data = StockHistoricalDataClient(key, secret)
        acct = self.trading.get_account()
        assert_paper(key, paper_flag, self.base_url, account=acct)  # post-connect
        self.account_number = getattr(acct, "account_number", "?")

    # ---- account state ---------------------------------------------------
    def account(self):
        a = self.trading.get_account()
        assert_paper(self._key, self._paper_flag, self.base_url, account=a)
        return a

    def equity(self):
        return float(self.account().equity)

    def positions(self):
        """symbol -> signed market value in dollars."""
        return {p.symbol: float(p.market_value)
                for p in self.trading.get_all_positions()}

    def position_qty(self):
        return {p.symbol: float(p.qty) for p in self.trading.get_all_positions()}

    def account_flags(self):
        a = self.account()
        flags = []
        if getattr(a, "trading_blocked", False):
            flags.append("trading_blocked")
        if getattr(a, "account_blocked", False):
            flags.append("account_blocked")
        if getattr(a, "transfers_blocked", False):
            flags.append("transfers_blocked")
        return flags

    def clock(self):
        return self.trading.get_clock()

    # ---- market data -----------------------------------------------------
    def daily_bars(self, symbols, lookback_days=400):
        """Recent daily bars for live signal computation.

        NOTE: this is the LIVE market cache. It is written to
        live/market_cache/ and the research loader refuses to read that path,
        so the research TRAIN/TEST split stays intact.
        """
        end = datetime.now(timezone.utc) - timedelta(minutes=20)  # SIP delay
        start = end - timedelta(days=lookback_days)
        req = StockBarsRequest(symbol_or_symbols=list(symbols),
                               timeframe=TimeFrame.Day, start=start, end=end,
                               adjustment="all")   # split + dividend adjusted
        bars = self.data.get_stock_bars(req).df
        MARKET_CACHE.mkdir(exist_ok=True)
        out = {}
        for sym in symbols:
            if sym not in bars.index.get_level_values(0):
                continue
            d = bars.xs(sym, level=0).copy()
            d.index = pd.to_datetime(d.index).tz_convert(None).normalize()
            d = d.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                  "close": "Close", "volume": "Volume"})
            d.index.name = "Date"
            d[["Open", "High", "Low", "Close", "Volume"]].to_csv(
                MARKET_CACHE / f"{sym}.csv")
            out[sym] = d
        return out

    # ---- orders ----------------------------------------------------------
    def submit(self, symbol, notional, side, as_of, reason, ref_price):
        """Market-on-open order for the NEXT session.

        Alpaca rejects fractional quantities with time-in-force OPG
        ("fractional orders must be DAY orders"), and a DAY order would fill
        at an arbitrary intraday price - breaking the decide-at-close /
        execute-at-next-open rule the whole backtest is built on. So the
        notional is converted to WHOLE shares at the reference close and any
        fractional remainder is deliberately dropped as dust.
        """
        qty = int(abs(float(notional)) // float(ref_price))
        if qty < 1:
            journal.rejected(as_of, symbol,
                             f"rounds to 0 whole shares at ${ref_price:.2f} "
                             f"(notional ${abs(float(notional)):.2f})")
            return None
        return self.submit_qty(symbol, qty, side, as_of, reason, ref_price)

    def submit_qty(self, symbol, qty, side, as_of, reason, ref_price,
                   tif="OPG", **journal_extra):
        """Submit a whole-share market order with an explicit time-in-force.

        TIF is a real risk decision, so it is never defaulted silently at the
        call site: OPG is the book's normal path (fill in the opening auction,
        matching the backtest), DAY is only used by the post-open
        reconciliation when an OPG order expired unfilled in that auction.
        """
        acct = self.account()
        assert_paper(self._key, self._paper_flag, self.base_url, account=acct)
        qty = int(qty)
        if qty < 1:
            return None
        tif_enum = {"OPG": TimeInForce.OPG, "DAY": TimeInForce.DAY}[tif]
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=tif_enum)
        o = self.trading.submit_order(req)
        journal.order(as_of, symbol, side, qty=qty,
                      notional=qty * float(ref_price), reason=reason,
                      order_id=str(o.id), tif=tif, ref_price=float(ref_price),
                      account=self.account_number, **journal_extra)
        return o

    def close_all(self, as_of, reason):
        """Flatten everything. Used only by the tier-2 emergency switch."""
        assert_paper(self._key, self._paper_flag, self.base_url,
                     account=self.account())
        journal.event(as_of, "FLATTEN_ALL", {"reason": reason}, severity="critical")
        # cancel_orders=True so resting orders cannot re-open the book
        self.trading.close_all_positions(cancel_orders=True)

    def open_orders(self):
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest
        return self.trading.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))

    def open_order_symbols(self):
        """Symbols with resting orders, ours or otherwise."""
        return [o.symbol for o in self.open_orders()]

    def pending_qty(self):
        """symbol -> net signed share quantity of UNFILLED resting orders.

        Pending orders are already-committed exposure. Ignoring them makes a
        second run in the same session re-submit the whole book, doubling it.
        """
        out = {}
        for o in self.open_orders():
            q = float(o.qty or 0) - float(o.filled_qty or 0)
            if o.side.value == "sell":
                q = -q
            out[o.symbol] = out.get(o.symbol, 0.0) + q
        return out

    def expired_today(self):
        """OPG orders that died in TODAY's opening auction without filling.

        `expired` is Alpaca's terminal state for an auction-only order that the
        opening auction did not execute. It is not an error and carries no
        reject reason - the order simply never traded, so the book is flat
        where it intended to be long.
        """
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest
        today = trading_day()
        req = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            after=datetime.now(timezone.utc) - timedelta(days=2),
            limit=200)
        out = []
        for o in self.trading.get_orders(req):
            if str(getattr(o.status, "value", o.status)) != "expired":
                continue
            when = getattr(o, "expired_at", None) or getattr(o, "updated_at", None)
            if when is None or when.astimezone(EXCHANGE_TZ).date() != today:
                continue
            out.append(o)
        return out

    def last_price(self, symbol, fallback=None):
        """Latest trade price, falling back to the cached daily close."""
        try:
            from alpaca.data.requests import StockLatestTradeRequest
            t = self.data.get_stock_latest_trade(
                StockLatestTradeRequest(symbol_or_symbols=symbol))
            return float(t[symbol].price)
        except Exception:  # noqa: BLE001 - price staleness is handled by caller
            if fallback is not None:
                return float(fallback)
            path = MARKET_CACHE / f"{symbol}.csv"
            if path.exists():
                return float(pd.read_csv(path, index_col=0)["Close"].iloc[-1])
            raise

    def cancel_open_orders(self):
        self.trading.cancel_orders()

    def recent_fills(self, since_days=8):
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest
        req = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            after=datetime.now(timezone.utc) - timedelta(days=since_days))
        return [o for o in self.trading.get_orders(req)
                if getattr(o, "filled_at", None)]
