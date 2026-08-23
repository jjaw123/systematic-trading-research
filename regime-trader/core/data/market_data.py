"""Market data: historical bars, live streams, quotes, and snapshots.

All data enters the system here, so timestamp hygiene lives in one place:
bars are validated (sorted, deduped, positive prices), the still-forming
bar is dropped to prevent intraday look-ahead, and session gaps (weekends,
holidays, halts) are left as-is — never filled — with unusually long gaps
logged for inspection.
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestBarRequest,
    StockLatestQuoteRequest,
    StockSnapshotRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from core.broker.alpaca_client import AlpacaClient

logger = logging.getLogger("regime_trader.data")

BAR_COLUMNS = ["open", "high", "low", "close", "volume"]
_TIMEFRAME_RE = re.compile(r"^(\d+)(Min|Hour|Day|Week|Month)$")
_UNITS = {"Min": TimeFrameUnit.Minute, "Hour": TimeFrameUnit.Hour,
          "Day": TimeFrameUnit.Day, "Week": TimeFrameUnit.Week,
          "Month": TimeFrameUnit.Month}
#: Calendar-day gaps longer than this get logged (halts/data problems);
#: normal weekends and holidays stay under it.
GAP_WARN_DAYS = 5


def parse_timeframe(timeframe: str) -> TimeFrame:
    """Parse Alpaca-notation timeframes: '1Day', '5Min', '1Hour', ..."""
    m = _TIMEFRAME_RE.match(timeframe)
    if not m:
        raise ValueError(f"invalid timeframe '{timeframe}' "
                         "(expected e.g. '1Day', '5Min', '1Hour')")
    return TimeFrame(int(m.group(1)), _UNITS[m.group(2)])


def validate_bars(bars: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
    """Sanity-check bars: sort, dedupe, drop NaNs, require positive prices.

    Session gaps are preserved (bars exist only for trading sessions);
    gaps longer than GAP_WARN_DAYS calendar days are logged, not filled.
    """
    out = bars.sort_index()
    dupes = out.index.duplicated(keep="last")
    if dupes.any():
        logger.warning("%s: dropping %d duplicate bar timestamps",
                       symbol, int(dupes.sum()))
        out = out[~dupes]
    n_before = len(out)
    out = out.dropna(subset=[c for c in BAR_COLUMNS if c in out.columns])
    if len(out) < n_before:
        logger.warning("%s: dropped %d bars with missing fields",
                       symbol, n_before - len(out))
    price_cols = [c for c in ("open", "high", "low", "close")
                  if c in out.columns]
    bad = (out[price_cols] <= 0).any(axis=1)
    if bad.any():
        logger.warning("%s: dropping %d bars with non-positive prices",
                       symbol, int(bad.sum()))
        out = out[~bad]
    if len(out) > 1:
        gaps = out.index.to_series().diff()
        long_gaps = gaps[gaps > pd.Timedelta(days=GAP_WARN_DAYS)]
        for ts, gap in long_gaps.items():
            logger.info("%s: %s gap ending %s (holiday/halt?)",
                        symbol, gap, ts)
    return out


class MarketData:
    """Historical + real-time market data via Alpaca.

    Args:
        client: Connected :class:`AlpacaClient` (used for the historical
            client, credentials for streams, and the market clock).
        timeframe: Default bar timeframe (Alpaca notation).
    """

    def __init__(self, client: AlpacaClient, timeframe: str = "1Day") -> None:
        self.client = client
        self.timeframe = timeframe
        self._stream: Any = None
        self._stream_thread: threading.Thread | None = None

    # ------------------------------------------------------------ historical

    def get_historical_bars(
        self,
        symbols: str | list[str],
        start: datetime,
        end: datetime | None = None,
        timeframe: str | None = None,
    ) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """Fetch validated OHLCV bars.

        The still-forming bar (today's, while the market is open) is
        dropped so consumers never see partial intraday data.

        Args:
            symbols: One symbol (returns a DataFrame) or a list (returns
                {symbol: DataFrame}).
            start: Inclusive range start.
            end: Inclusive range end; defaults to now.
            timeframe: Override of the default timeframe.

        Returns:
            OHLCV frame(s) indexed by UTC timestamp.
        """
        single = isinstance(symbols, str)
        symbol_list = [symbols] if single else list(symbols)
        request = StockBarsRequest(
            symbol_or_symbols=symbol_list,
            timeframe=parse_timeframe(timeframe or self.timeframe),
            start=start, end=end,
        )
        raw = self.client._call(self.client.data.get_stock_bars, request).df
        out: dict[str, pd.DataFrame] = {}
        for sym in symbol_list:
            if raw.empty or sym not in raw.index.get_level_values(0):
                logger.warning("no bars returned for %s", sym)
                out[sym] = pd.DataFrame(columns=BAR_COLUMNS)
                continue
            df = raw.xs(sym, level=0)[BAR_COLUMNS].copy()
            df = validate_bars(df, sym)
            out[sym] = self._drop_forming_bar(df)
        return out[symbols] if single else out

    def _drop_forming_bar(self, bars: pd.DataFrame) -> pd.DataFrame:
        """Drop the last bar when it is still forming (today, market open)."""
        if bars.empty:
            return bars
        try:
            market_open = self.client.is_market_open()
        except Exception:
            market_open = False  # can't tell — keep the bar
        if not market_open:
            return bars
        last_ts = bars.index[-1]
        now = datetime.now(timezone.utc)
        if last_ts.date() == now.date():
            logger.debug("dropping still-forming bar at %s", last_ts)
            return bars.iloc[:-1]
        return bars

    # --------------------------------------------------------------- latest

    def get_latest_bar(self, symbol: str) -> dict[str, Any]:
        """Latest completed bar for one symbol."""
        result = self.client._call(
            self.client.data.get_stock_latest_bar,
            StockLatestBarRequest(symbol_or_symbols=symbol))
        bar = result[symbol]
        return {"symbol": symbol, "timestamp": bar.timestamp,
                "open": float(bar.open), "high": float(bar.high),
                "low": float(bar.low), "close": float(bar.close),
                "volume": float(bar.volume)}

    def get_latest_quote(self, symbol: str) -> dict[str, Any]:
        """Latest quote with the spread fields the risk manager checks."""
        result = self.client._call(
            self.client.data.get_stock_latest_quote,
            StockLatestQuoteRequest(symbol_or_symbols=symbol))
        quote = result[symbol]
        bid, ask = float(quote.bid_price), float(quote.ask_price)
        mid = (bid + ask) / 2 if bid > 0 and ask > 0 else None
        return {"symbol": symbol, "timestamp": quote.timestamp,
                "bid": bid, "ask": ask,
                "bid_size": float(quote.bid_size),
                "ask_size": float(quote.ask_size),
                "spread_pct": (ask - bid) / mid if mid else None,
                "tradable": True}

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        """Combined snapshot: latest quote, trade, and daily bar."""
        result = self.client._call(
            self.client.data.get_stock_snapshot,
            StockSnapshotRequest(symbol_or_symbols=symbol))
        snap = result[symbol]
        daily = snap.daily_bar
        return {
            "symbol": symbol,
            "latest_price": float(snap.latest_trade.price)
            if snap.latest_trade else None,
            "bid": float(snap.latest_quote.bid_price)
            if snap.latest_quote else None,
            "ask": float(snap.latest_quote.ask_price)
            if snap.latest_quote else None,
            "daily_open": float(daily.open) if daily else None,
            "daily_high": float(daily.high) if daily else None,
            "daily_low": float(daily.low) if daily else None,
            "daily_close": float(daily.close) if daily else None,
            "daily_volume": float(daily.volume) if daily else None,
        }

    # -------------------------------------------------------------- streams

    def _ensure_stream(self) -> Any:
        if self._stream is None:
            from alpaca.data.live import StockDataStream  # lazy import
            self._stream = StockDataStream(self.client.api_key,
                                           self.client.secret_key)
        return self._stream

    def subscribe_bars(self, symbols: list[str],
                       callback: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe to live bars; callback gets one plain dict per bar."""
        stream = self._ensure_stream()

        async def _handler(bar: Any) -> None:
            try:
                callback({"symbol": bar.symbol, "timestamp": bar.timestamp,
                          "open": float(bar.open), "high": float(bar.high),
                          "low": float(bar.low), "close": float(bar.close),
                          "volume": float(bar.volume)})
            except Exception:
                logger.exception("bar callback failed")

        stream.subscribe_bars(_handler, *symbols)
        logger.info("subscribed to bars: %s", symbols)

    def subscribe_quotes(self, symbols: list[str],
                         callback: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe to live quotes (for spread checks before orders)."""
        stream = self._ensure_stream()

        async def _handler(quote: Any) -> None:
            try:
                bid, ask = float(quote.bid_price), float(quote.ask_price)
                mid = (bid + ask) / 2 if bid > 0 and ask > 0 else None
                callback({"symbol": quote.symbol,
                          "timestamp": quote.timestamp, "bid": bid,
                          "ask": ask,
                          "spread_pct": (ask - bid) / mid if mid else None})
            except Exception:
                logger.exception("quote callback failed")

        stream.subscribe_quotes(_handler, *symbols)
        logger.info("subscribed to quotes: %s", symbols)

    def start_stream(self) -> None:
        """Run the data stream in a daemon thread (after subscribing)."""
        stream = self._ensure_stream()
        self._stream_thread = threading.Thread(target=stream.run,
                                               name="market-data",
                                               daemon=True)
        self._stream_thread.start()
        logger.info("market data stream started")

    def stop_stream(self) -> None:
        """Close the websocket stream cleanly."""
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                logger.exception("stream stop failed")
            self._stream = None
            logger.info("market data stream stopped")
