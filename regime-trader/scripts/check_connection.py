"""Verify the Alpaca paper connection and optionally place a test trade.

Usage (from the regime-trader directory):
    python scripts/check_connection.py                 # connectivity only
    python scripts/check_connection.py --trade NVDA    # + 1-share test bracket

The test trade goes through the system's real execution path
(OrderExecutor.submit_bracket_order): entry limit at the last price, stop 5%
below, take-profit at 2R — so even a fire-and-forget test carries a stop.
Paper endpoint only unless ALPACA_PAPER=false is confirmed interactively.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from core.broker.alpaca_client import LIVE_URL, PAPER_URL, AlpacaClient
from core.broker.order_executor import OrderExecutor
from core.data.market_data import MarketData
from core.regime_strategies import Direction, Signal


def make_test_signal(symbol: str, last_price: float) -> Signal:
    entry = round(last_price, 2)
    return Signal(
        symbol=symbol, direction=Direction.LONG, confidence=1.0,
        entry_price=entry, stop_loss=round(entry * 0.95, 2),
        take_profit=None, position_size_pct=0.0, leverage=1.0,
        regime_id=-1, regime_name="connection_test", regime_probability=1.0,
        timestamp=None, reasoning="manual connectivity test",
        strategy_name="check_connection",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Alpaca connectivity check")
    parser.add_argument("--trade", metavar="SYMBOL", default=None,
                        help="also place a 1-share test bracket order")
    parser.add_argument("--qty", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    load_dotenv()

    client = AlpacaClient.from_env()
    base_url = PAPER_URL if client.paper else LIVE_URL
    print(f"\nendpoint: {base_url}/v2 ({'PAPER' if client.paper else 'LIVE'})")

    account = client.connect()  # health check inside
    print(f"account:  status={account['status']} equity=${account['equity']:,.2f} "
          f"cash=${account['cash']:,.2f} buying_power=${account['buying_power']:,.2f}")
    clock = client.get_clock()
    print(f"market:   {'OPEN' if clock['is_open'] else 'CLOSED'} "
          f"(next open {clock['next_open']}, next close {clock['next_close']})")
    print("✅ Alpaca API connected\n")

    if not args.trade:
        return 0

    symbol = args.trade.upper()
    snapshot = MarketData(client).get_snapshot(symbol)
    last = snapshot["latest_price"] or snapshot["daily_close"]
    if not last:
        print(f"❌ no price available for {symbol}")
        return 1
    signal = make_test_signal(symbol, last)
    record = OrderExecutor(client).submit_bracket_order(signal, qty=args.qty)
    order = client.get_order(record.order_id)
    print(f"test trade placed: {args.qty} {symbol} @ limit "
          f"{record.limit_price:.2f} (last {last:.2f})")
    print(f"  trade_id: {record.trade_id}")
    print(f"  order id: {record.order_id}  status: {order['status']}")
    print(f"  stop: {signal.stop_loss:.2f}  legs: {len(order.get('legs', []))}")
    if not clock["is_open"]:
        print("  note: market is closed — the order is queued and will work "
              "at the next open; cancel it from the Alpaca dashboard if "
              "unwanted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
