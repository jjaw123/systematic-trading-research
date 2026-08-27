"""Daily live loop (paper only).

Run after each close:

    python research/live/daily_loop.py

Sequence, in this order for a reason:
  1. connect + verify paper account (four checks)
  2. pull fresh daily bars for the traded universe
  3. TIER-2 emergency scan -> if anything looks wrong: FLATTEN + HALT, stop
  4. TIER-1 performance halt check -> if halted: no new entries (exits still run)
  5. compute target weights from yesterday's close (IDEA-109 risk-layer book)
  6. diff against current positions, gate every order through hard limits
  7. submit market-on-open orders for the next session
  8. journal a snapshot and append to live_returns.csv

Every step writes to JOURNAL.jsonl. Nothing is submitted without a reason
string recorded alongside it.
"""

import sys
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import journal  # noqa: E402
from live.broker import PaperBroker, trading_day  # noqa: E402
from live.config import (  # noqa: E402
    LIVE_RETURNS_PATH,
    MAX_DATA_STALENESS_DAYS,
    REFERENCE_SYMBOLS,
    RISK_PCT_PER_TRADE,
    TRADED_UNIVERSE,
    WARMUP_TRADING_DAYS,
)
from live.halt import entries_allowed, run_daily_check  # noqa: E402
from live.limits import check_order, detect_emergency  # noqa: E402
from live.state import bump_api_errors, read_runtime, reset_api_errors, write_runtime  # noqa: E402
from strategies.risklayer import make  # noqa: E402

EMERGENCY_STATE = Path(__file__).resolve().parent / "EMERGENCY_HALT.json"


def compute_targets(bars):
    """Target weights decided from the latest CLOSE, executed at next open."""
    strat = make(RISK_PCT_PER_TRADE, levered=False)
    w = strat(bars)
    return w.iloc[-1].to_dict(), w.index[-1]


def trigger_emergency(broker, as_of, problems):
    """Tier 2: flatten everything, halt, and refuse to resume automatically."""
    import json
    journal.event(as_of, "EMERGENCY_TRIGGERED", {"problems": problems},
                  severity="critical")
    try:
        broker.close_all(as_of, reason="; ".join(problems))
        flattened = True
    except Exception as ex:  # noqa: BLE001
        flattened = False
        journal.event(as_of, "FLATTEN_FAILED", {"error": str(ex)},
                      severity="critical")
    EMERGENCY_STATE.write_text(json.dumps({
        "halted": True, "since": str(as_of), "problems": problems,
        "flattened": flattened, "cleared_by": None,
        "note": "Clear ONLY by hand after investigating. There is no auto-resume."
    }, indent=2))
    print("!!! EMERGENCY HALT — book flattened. Reasons:")
    for p in problems:
        print(f"!!!   - {p}")
    return flattened


def emergency_active():
    import json
    if not EMERGENCY_STATE.exists():
        return False, ""
    try:
        s = json.loads(EMERGENCY_STATE.read_text())
    except (OSError, ValueError):
        return True, "EMERGENCY_HALT.json unreadable — failing closed"
    if s.get("halted"):
        return True, f"emergency halt since {s.get('since')}: {s.get('problems')}"
    return False, ""


def main():
    # Exchange time, not UTC: the UTC date rolls at 20:00 ET, so an evening
    # run would label itself with tomorrow's date and file its equity point on
    # the wrong day.
    as_of = trading_day()
    rt = read_runtime()

    blocked, why = emergency_active()
    if blocked:
        journal.event(as_of, "run_aborted", {"reason": why}, severity="critical")
        print(f"EMERGENCY HALT ACTIVE — {why}\nNo orders. Clear by hand to resume.")
        return 4

    try:
        broker = PaperBroker()
    except Exception as ex:  # noqa: BLE001
        journal.event(as_of, "broker_connect_failed", {"error": str(ex)},
                      severity="critical")
        print(f"Broker connect failed (refusing to trade): {ex}")
        bump_api_errors()
        return 3
    journal.event(as_of, "connected", {"account": broker.account_number,
                                       "mode": "PAPER"})

    # --- data -------------------------------------------------------------
    try:
        bars = broker.daily_bars(TRADED_UNIVERSE + REFERENCE_SYMBOLS,
                                 lookback_days=int(WARMUP_TRADING_DAYS * 1.6))
        reset_api_errors()
    except Exception as ex:  # noqa: BLE001
        n = bump_api_errors()
        journal.event(as_of, "data_fetch_failed", {"error": str(ex),
                                                   "consecutive": n},
                      severity="error")
        print(f"Data fetch failed ({n} consecutive): {ex}")
        return 3

    missing = [s for s in TRADED_UNIVERSE if s not in bars]
    latest = max((d.index[-1] for d in bars.values()), default=None)
    staleness = (pd.Timestamp(as_of) - latest).days if latest is not None else 999

    # --- TIER 2: integrity scan (flatten + halt) --------------------------
    try:
        equity = broker.equity()
        positions = broker.positions()
        flags = broker.account_flags()
        resting = broker.open_order_symbols()
        pending = broker.pending_qty()
    except Exception as ex:  # noqa: BLE001
        n = bump_api_errors()
        journal.event(as_of, "account_read_failed", {"error": str(ex),
                                                     "consecutive": n},
                      severity="error")
        print(f"Account read failed: {ex}")
        return 3

    problems = detect_emergency(equity, positions, staleness,
                                rt.get("consecutive_api_errors", 0), flags,
                                open_order_symbols=resting)
    if missing:
        problems.append(f"no bars returned for {missing}")
    if problems:
        trigger_emergency(broker, as_of, problems)
        return 4

    # --- TIER 1: performance halt (entries only) --------------------------
    if LIVE_RETURNS_PATH.exists():
        live = pd.read_csv(LIVE_RETURNS_PATH, index_col=0, parse_dates=True).sort_index()
        if len(live) > 1:
            spy = bars["SPY"]["Close"].pct_change()
            run_daily_check(live, spy)
    allow_entries, halt_why = entries_allowed()
    if not allow_entries:
        journal.event(as_of, "entries_blocked", {"reason": halt_why},
                      severity="warning")
        print(f"TIER-1 HALT: new entries blocked — {halt_why}")

    # --- signals ----------------------------------------------------------
    targets, signal_date = compute_targets(bars)
    journal.event(as_of, "signals_computed",
                  {"signal_date": str(signal_date.date()),
                   "targets": {k: round(v, 4) for k, v in targets.items()
                               if abs(v) > 1e-9}})

    # --- diff to orders ---------------------------------------------------
    orders_today = 0
    for symbol in TRADED_UNIVERSE:
        target_w = float(targets.get(symbol, 0.0))
        last_px = float(bars[symbol]["Close"].iloc[-1])
        # Committed exposure = filled positions PLUS unfilled resting orders.
        # Counting only positions makes a second run in the same session
        # re-submit the entire book.
        pending_val = pending.get(symbol, 0.0) * last_px
        current_val = positions.get(symbol, 0.0) + pending_val
        current_w = current_val / equity if equity else 0.0
        delta_w = target_w - current_w
        delta_notional = delta_w * equity
        is_reducing = abs(target_w) < abs(current_w)

        journal.decision(as_of, symbol, target_w, current_w,
                         reason=f"risk-layer target from {signal_date.date()} close",
                         held_value=round(positions.get(symbol, 0.0), 2),
                         pending_value=round(pending_val, 2))

        if abs(delta_notional) < 1.0:
            continue
        if delta_w > 0 and not allow_entries and not is_reducing:
            journal.rejected(as_of, symbol, "tier-1 halt: new entries blocked")
            continue

        verdict = check_order(symbol, delta_notional, equity, positions,
                              orders_today, is_reducing)
        if not verdict.allowed:
            journal.rejected(as_of, symbol, verdict.reason,
                             wanted_notional=round(delta_notional, 2))
            continue
        side = "buy" if delta_notional > 0 else "sell"
        try:
            o = broker.submit(symbol, verdict.adjusted_notional, side, as_of,
                              reason=f"{verdict.reason}; target {target_w:.3f} "
                                     f"vs current {current_w:.3f} "
                                     f"(incl. pending)",
                              ref_price=last_px)
            if o is not None:
                orders_today += 1
        except Exception as ex:  # noqa: BLE001
            n = bump_api_errors()
            journal.event(as_of, "order_failed",
                          {"symbol": symbol, "error": str(ex), "consecutive": n},
                          severity="error")

    gross = sum(abs(v) for v in positions.values()) / equity if equity else 0.0
    journal.snapshot(as_of, equity, {k: round(v, 2) for k, v in positions.items()},
                     gross, halted=not allow_entries, orders_submitted=orders_today)
    write_runtime({**rt, "last_run": str(as_of), "last_equity": equity})
    _append_equity(as_of, equity, gross)
    print(f"[{as_of}] equity ${equity:,.2f} | gross {gross:.1%} | "
          f"{orders_today} orders | entries {'BLOCKED' if not allow_entries else 'ok'}")
    return 0


def _append_equity(as_of, equity, gross):
    """Maintain live_returns.csv, which the tier-1 checks consume."""
    if LIVE_RETURNS_PATH.exists():
        df = pd.read_csv(LIVE_RETURNS_PATH, index_col=0, parse_dates=True).sort_index()
    else:
        df = pd.DataFrame(columns=["equity", "net_return", "gross_exposure"])
    prev = df["equity"].iloc[-1] if len(df) else equity
    ret = (equity / prev - 1.0) if prev else 0.0
    df.loc[pd.Timestamp(as_of)] = {"equity": equity, "net_return": ret,
                                   "gross_exposure": gross}
    df.sort_index().to_csv(LIVE_RETURNS_PATH)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        journal.event(trading_day(), "unhandled_exception",
                      {"traceback": traceback.format_exc()}, severity="critical")
        traceback.print_exc()
        sys.exit(3)
