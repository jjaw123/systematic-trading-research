"""Hard-limit enforcement and tier-2 emergency detection.

Two tiers of shutdown, deliberately different in what they do:

  TIER 1  performance halt (live/halt.py, thresholds in HALT_RULES.yaml)
          -> block NEW entries, let existing positions exit normally.
          Rationale: performance decay is not an emergency, and dumping a
          book at the worst tick is its own disaster.

  TIER 2  integrity emergency (this file)
          -> FLATTEN EVERYTHING and halt.
          Rationale: if the system's own state is wrong - unknown symbols,
          stale data, exposure past the hard caps, repeated API failures -
          then we no longer know what we own, and every further order is
          made blind. Getting flat is the only safe action.

Performance decay never triggers a flatten. System malfunction always does.
"""

from dataclasses import dataclass

from .config import (
    MAX_CONSECUTIVE_API_ERRORS,
    MAX_DATA_STALENESS_DAYS,
    MAX_GROSS_EXPOSURE,
    MAX_OPEN_POSITIONS,
    MAX_ORDER_PCT,
    MAX_ORDERS_PER_DAY,
    MAX_POSITION_PCT,
    MIN_ORDER_NOTIONAL,
    TRADED_UNIVERSE,
    UNEXPECTED_SYMBOL_IS_FATAL,
)


@dataclass
class LimitVerdict:
    allowed: bool
    reason: str
    adjusted_notional: float = 0.0


def check_order(symbol, notional, equity, current_positions, orders_today,
                is_reducing):
    """Gate one order against the in-code hard limits.

    `is_reducing` orders (trimming or closing) are always permitted to pass
    the count/exposure caps - refusing to let a book shrink would turn a
    limit breach into a trap.
    """
    if equity <= 0:
        return LimitVerdict(False, "non-positive equity")
    if symbol not in TRADED_UNIVERSE:
        return LimitVerdict(False, f"{symbol} is not in the traded universe")
    if orders_today >= MAX_ORDERS_PER_DAY:
        return LimitVerdict(False, f"daily order cap {MAX_ORDERS_PER_DAY} reached")
    if abs(notional) < MIN_ORDER_NOTIONAL and not is_reducing:
        return LimitVerdict(False, f"below min notional {MIN_ORDER_NOTIONAL}")

    if is_reducing:
        return LimitVerdict(True, "reducing exposure", abs(notional))

    held = {s: v for s, v in current_positions.items() if abs(v) > 1e-9}

    if symbol not in held and len(held) >= MAX_OPEN_POSITIONS:
        return LimitVerdict(False,
                            f"max open positions {MAX_OPEN_POSITIONS} reached")

    # Caps COMPOSE: each one only ever tightens the size, and the binding one
    # wins. Returning early on the first cap hit would let a later cap be
    # breached (e.g. an order trimmed to 25% of equity that still pushes the
    # position itself past 25%).
    allowed_notional = abs(notional)
    reasons = []

    order_room = MAX_ORDER_PCT * equity
    if allowed_notional > order_room:
        allowed_notional = order_room
        reasons.append(f"order cap {MAX_ORDER_PCT:.0%}")

    pos_room = MAX_POSITION_PCT * equity - abs(held.get(symbol, 0.0))
    if allowed_notional > pos_room:
        allowed_notional = pos_room
        reasons.append(f"position cap {MAX_POSITION_PCT:.0%}")

    gross_room = MAX_GROSS_EXPOSURE * equity - sum(abs(v) for v in held.values())
    if allowed_notional > gross_room:
        allowed_notional = gross_room
        reasons.append(f"gross cap {MAX_GROSS_EXPOSURE:.0%}")

    if allowed_notional < MIN_ORDER_NOTIONAL:
        return LimitVerdict(False,
                            f"no room left after {' + '.join(reasons) or 'limits'}")
    if reasons:
        return LimitVerdict(True, f"trimmed by {' + '.join(reasons)}",
                            allowed_notional)
    return LimitVerdict(True, "within limits", allowed_notional)


def detect_emergency(equity, positions, data_age_days, consecutive_api_errors,
                     account_flags=None, open_order_symbols=None):
    """Tier-2 scan: does the system's own state look wrong?

    Returns a list of reasons. Non-empty => FLATTEN EVERYTHING AND HALT.

    Open orders are checked as well as positions: an unknown resting order is
    a future unknown position, and catching it before it fills is the whole
    point of looking.
    """
    problems = []

    if UNEXPECTED_SYMBOL_IS_FATAL and open_order_symbols:
        stray_orders = sorted(set(open_order_symbols) - set(TRADED_UNIVERSE))
        if stray_orders:
            problems.append(f"open orders for symbols outside the book: "
                            f"{stray_orders}")

    if equity is None or equity <= 0:
        problems.append(f"account equity is {equity!r}")

    held = {s: v for s, v in (positions or {}).items() if abs(v) > 1e-9}

    if UNEXPECTED_SYMBOL_IS_FATAL:
        strays = sorted(set(held) - set(TRADED_UNIVERSE))
        if strays:
            problems.append(f"holding symbols the book never chose: {strays}")

    if equity and equity > 0:
        gross = sum(abs(v) for v in held.values())
        if gross > MAX_GROSS_EXPOSURE * equity * 1.02:   # 2% tolerance for drift
            problems.append(f"gross exposure {gross/equity:.1%} exceeds hard cap "
                            f"{MAX_GROSS_EXPOSURE:.0%}")
        for sym, val in held.items():
            if abs(val) > MAX_POSITION_PCT * equity * 1.02:
                problems.append(f"{sym} at {abs(val)/equity:.1%} exceeds position "
                                f"cap {MAX_POSITION_PCT:.0%}")

    if len(held) > MAX_OPEN_POSITIONS:
        problems.append(f"{len(held)} open positions exceeds cap {MAX_OPEN_POSITIONS}")

    if data_age_days is not None and data_age_days > MAX_DATA_STALENESS_DAYS:
        problems.append(f"market data is {data_age_days} days stale "
                        f"(max {MAX_DATA_STALENESS_DAYS}) - trading blind")

    if consecutive_api_errors >= MAX_CONSECUTIVE_API_ERRORS:
        problems.append(f"{consecutive_api_errors} consecutive broker API errors")

    for flag in (account_flags or []):
        problems.append(f"broker account flag: {flag}")

    return problems
