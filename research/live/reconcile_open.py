"""Post-open reconciliation (paper only).

Run a few minutes after the open, on every trading day:

    python research/live/reconcile_open.py

The nightly loop submits market-on-open (OPG) orders so live fills match the
backtest's decide-at-close / execute-at-next-open rule. OPG orders are
auction-only: anything the opening auction does not execute is EXPIRED by
Alpaca a minute or two later, unfilled and unrecoverable. On 2026-08-24 all
four of the book's orders expired that way and the account sat flat all day
while the strategy believed it was invested.

This script closes that hole. It finds today's expired OPG orders, works out
what is still uncovered, and resubmits the remainder as DAY market orders,
through the same hard limits and the same tier-1 halt gate as any other
order. The cost is a few minutes of slippage versus the opening print on the
days the auction fails; the alternative is a book that silently never trades.

Order of operations mirrors daily_loop for a reason:
  1. emergency-halt check  -> if halted, do nothing at all
  2. connect + verify paper account
  3. market must be OPEN, and it must still be within an hour of the open
  4. find today's expired orders, subtract fills and live resting orders
  5. gate every replacement through hard limits + tier-1 halt
  6. submit DAY market orders, journalling `replaces: <original id>`

Idempotent: replacements are journalled with the id of the order they
replace, and an id that already appears is never replaced twice. Running this
five times in a row submits the same orders exactly once.

Exit codes: 0 done (including nothing to do), 3 broker/API failure,
4 emergency halt active.
"""

import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import journal  # noqa: E402
from live.broker import EXCHANGE_TZ, PaperBroker, trading_day  # noqa: E402
from live.config import TRADED_UNIVERSE  # noqa: E402
from live.daily_loop import emergency_active  # noqa: E402
from live.halt import entries_allowed  # noqa: E402
from live.limits import check_order  # noqa: E402
from live.state import bump_api_errors, reset_api_errors  # noqa: E402


# A replacement is a repair of the opening auction, not a licence to trade at
# any hour. Under launchd a job missed while the machine slept runs on WAKE,
# so this script can fire at 14:00 for a 09:30 auction; filling then is a
# different trade at a different price, and the nightly loop will re-decide
# anyway. Outside the window it does nothing and says so.
MARKET_OPEN_ET = time(9, 30)
REPLACEMENT_WINDOW_MIN = 60


def within_replacement_window(now_et, window_min=REPLACEMENT_WINDOW_MIN):
    """True while it is still the same trade the opening auction refused."""
    minutes = (now_et.hour * 60 + now_et.minute) - \
              (MARKET_OPEN_ET.hour * 60 + MARKET_OPEN_ET.minute)
    return 0 <= minutes <= window_min


@dataclass(frozen=True)
class Replacement:
    symbol: str
    side: str          # "buy" / "sell"
    qty: int           # whole shares still uncovered
    original_id: str
    reason: str


def _signed(side, qty):
    return -abs(qty) if str(side).lower().endswith("sell") else abs(qty)


def plan_replacements(expired, already_replaced, pending_qty,
                      universe=TRADED_UNIVERSE):
    """Decide what to resubmit. Pure function - no broker, no clock.

    `expired`         objects with .id .symbol .side .qty .filled_qty
    `already_replaced` set of original order ids replaced on an earlier run
    `pending_qty`     symbol -> signed net UNFILLED shares resting right now

    A resting order in the same direction already commits that exposure, so it
    is netted off before deciding what is genuinely uncovered. Partial fills
    are netted off too. Anything outside the traded universe is left alone -
    the tier-2 scan owns unknown symbols, not this script.
    """
    remaining = dict(pending_qty)
    out = []
    for o in expired:
        oid = str(o.id)
        if oid in already_replaced:
            continue
        if o.symbol not in universe:
            continue
        want = _signed(getattr(o.side, "value", o.side),
                       float(o.qty or 0) - float(o.filled_qty or 0))
        if want == 0:
            continue
        covered = remaining.get(o.symbol, 0.0)
        if want > 0 and covered > 0:
            take = min(want, covered)
        elif want < 0 and covered < 0:
            take = max(want, covered)
        else:
            take = 0.0
        want -= take
        remaining[o.symbol] = covered - take
        qty = int(abs(want))
        if qty < 1:
            continue
        out.append(Replacement(
            symbol=o.symbol,
            side="buy" if want > 0 else "sell",
            qty=qty,
            original_id=oid,
            reason=f"OPG order {oid[:8]} expired unfilled in the opening "
                   f"auction; replacing with DAY market"))
    return out


def already_replaced_ids(records=None):
    """Original order ids this script has already acted on, from the journal."""
    records = journal.read_all() if records is None else records
    return {r["replaces"] for r in records
            if r.get("kind") == "order" and r.get("replaces")}


def orders_logged_today(as_of, records=None):
    records = journal.read_all() if records is None else records
    return sum(1 for r in records
               if r.get("kind") == "order" and r.get("as_of") == str(as_of))


def main():
    as_of = trading_day()

    blocked, why = emergency_active()
    if blocked:
        journal.event(as_of, "reconcile_aborted", {"reason": why},
                      severity="critical")
        print(f"EMERGENCY HALT ACTIVE — {why}\nNo replacements.")
        return 4

    try:
        broker = PaperBroker()
    except Exception as ex:  # noqa: BLE001
        journal.event(as_of, "broker_connect_failed", {"error": str(ex)},
                      severity="critical")
        print(f"Broker connect failed (refusing to trade): {ex}")
        bump_api_errors()
        return 3

    try:
        clock = broker.clock()
        if not getattr(clock, "is_open", False):
            journal.event(as_of, "reconcile_skipped",
                          {"reason": "market closed"})
            print("Market closed — nothing to reconcile.")
            return 0
        now_et = datetime.now(EXCHANGE_TZ)
        if not within_replacement_window(now_et):
            journal.event(as_of, "reconcile_skipped",
                          {"reason": f"{now_et:%H:%M} ET is outside the "
                                     f"{REPLACEMENT_WINDOW_MIN}-minute window "
                                     f"after the open"}, severity="warning")
            print(f"{now_et:%H:%M} ET — too late after the open to replace "
                  f"auction orders. Nothing submitted.")
            return 0
        expired = broker.expired_today()
        equity = broker.equity()
        positions = broker.positions()
        pending = broker.pending_qty()
        reset_api_errors()
    except Exception as ex:  # noqa: BLE001
        n = bump_api_errors()
        journal.event(as_of, "reconcile_read_failed",
                      {"error": str(ex), "consecutive": n}, severity="error")
        print(f"Account read failed: {ex}")
        return 3

    records = journal.read_all()
    plan = plan_replacements(expired, already_replaced_ids(records), pending)
    if not plan:
        journal.event(as_of, "reconcile_clean",
                      {"expired_seen": len(expired), "replacements": 0})
        print(f"[{as_of}] {len(expired)} expired order(s), nothing to replace.")
        return 0

    journal.event(as_of, "opg_expired",
                  {"orders": [{"symbol": r.symbol, "side": r.side,
                               "qty": r.qty, "original_id": r.original_id}
                              for r in plan]}, severity="warning")

    allow_entries, halt_why = entries_allowed()
    if not allow_entries:
        journal.event(as_of, "entries_blocked", {"reason": halt_why},
                      severity="warning")

    submitted = 0
    orders_today = orders_logged_today(as_of, records)
    # Replacements are gated one at a time, so each must see the exposure the
    # previous ones just committed - otherwise four 25% orders all pass the
    # gross cap against an empty book and the fills breach it together.
    projected = dict(positions)
    for r in plan:
        try:
            price = broker.last_price(r.symbol)
        except Exception as ex:  # noqa: BLE001
            journal.rejected(as_of, r.symbol, f"no price available: {ex}",
                             replaces=r.original_id)
            continue
        notional = r.qty * price * (1 if r.side == "buy" else -1)
        held = positions.get(r.symbol, 0.0)
        is_reducing = (r.side == "sell" and held > 0) or \
                      (r.side == "buy" and held < 0)
        if r.side == "buy" and not allow_entries and not is_reducing:
            journal.rejected(as_of, r.symbol, "tier-1 halt: new entries blocked",
                             replaces=r.original_id)
            continue
        verdict = check_order(r.symbol, notional, equity, projected,
                              orders_today, is_reducing)
        if not verdict.allowed:
            journal.rejected(as_of, r.symbol, verdict.reason,
                             wanted_notional=round(notional, 2),
                             replaces=r.original_id)
            continue
        # A cap may have trimmed the notional; re-derive whole shares from it.
        qty = min(r.qty, int(abs(verdict.adjusted_notional) // price))
        if qty < 1:
            journal.rejected(as_of, r.symbol,
                             f"rounds to 0 whole shares at ${price:.2f} after "
                             f"limits", replaces=r.original_id)
            continue
        try:
            o = broker.submit_qty(r.symbol, qty, r.side, as_of,
                                  reason=f"{r.reason}; {verdict.reason}",
                                  ref_price=price, tif="DAY",
                                  replaces=r.original_id)
            if o is not None:
                submitted += 1
                orders_today += 1
                projected[r.symbol] = projected.get(r.symbol, 0.0) + \
                    qty * price * (1 if r.side == "buy" else -1)
        except Exception as ex:  # noqa: BLE001
            n = bump_api_errors()
            journal.event(as_of, "order_failed",
                          {"symbol": r.symbol, "error": str(ex),
                           "consecutive": n, "replaces": r.original_id},
                          severity="error")

    print(f"[{as_of}] {len(expired)} expired | {len(plan)} to replace | "
          f"{submitted} DAY order(s) submitted"
          f"{' | entries BLOCKED' if not allow_entries else ''}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        journal.event(trading_day(), "unhandled_exception",
                      {"where": "reconcile_open",
                       "traceback": traceback.format_exc()},
                      severity="critical")
        traceback.print_exc()
        sys.exit(3)
