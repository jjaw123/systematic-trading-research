"""Safety tests for the live layer. These guard real money."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import config  # noqa: E402
from live.config import NotPaperAccount, assert_paper  # noqa: E402
from live.limits import check_order, detect_emergency  # noqa: E402

PAPER = config.PAPER_BASE_URL
LIVE = config.LIVE_BASE_URL


class FakeAcct:
    def __init__(self, number="PA3XYZ", status="ACTIVE"):
        self.account_number = number
        self.status = status


# ---- paper-only enforcement -----------------------------------------------

def test_real_money_is_off_by_default():
    assert config.REAL_MONEY_ENABLED is False


def test_paper_key_and_flags_pass():
    assert assert_paper("PKTEST123", True, PAPER, FakeAcct()) is True


def test_live_key_prefix_refused():
    with pytest.raises(NotPaperAccount, match="not a paper key"):
        assert_paper("AKLIVE999", True, PAPER, FakeAcct())


def test_live_endpoint_refused():
    with pytest.raises(NotPaperAccount, match="not the paper endpoint"):
        assert_paper("PKTEST123", True, LIVE, FakeAcct())


def test_paper_flag_false_refused():
    with pytest.raises(NotPaperAccount, match="ALPACA_PAPER is not true"):
        assert_paper("PKTEST123", False, PAPER, FakeAcct())


def test_live_account_number_refused():
    with pytest.raises(NotPaperAccount, match="does not look like a paper account"):
        assert_paper("PKTEST123", True, PAPER, FakeAcct(number="U1234567"))


def test_real_money_flag_alone_blocks_everything(monkeypatch):
    """Even a perfectly valid paper setup must refuse while the gate is on."""
    monkeypatch.setattr(config, "REAL_MONEY_ENABLED", True)
    with pytest.raises(NotPaperAccount, match="has not authorised live trading"):
        assert_paper("PKTEST123", True, PAPER, FakeAcct())


# ---- hard limits ----------------------------------------------------------

def test_position_cap_trims_order():
    v = check_order("XLK", 40_000, 100_000, {"XLK": 10_000}, 0, False)
    assert v.allowed and v.adjusted_notional == pytest.approx(15_000)  # 25% cap


def test_position_cap_blocks_when_already_full():
    v = check_order("XLK", 5_000, 100_000, {"XLK": 25_000}, 0, False)
    assert not v.allowed and "no room left" in v.reason


def test_caps_compose_rather_than_short_circuit():
    """An order trimmed by the order-size cap must STILL respect the position
    cap. Returning early on the first binding cap was a real defect."""
    v = check_order("XLK", 90_000, 100_000, {"XLK": 10_000}, 0, False)
    assert v.allowed
    assert v.adjusted_notional == pytest.approx(15_000)      # 25% pos cap binds
    assert 10_000 + v.adjusted_notional <= 0.25 * 100_000 + 1e-6


def test_max_open_positions_blocks_new_symbol():
    held = {s: 10_000 for s in ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP"]}
    v = check_order("XLU", 5_000, 100_000, held, 0, False)
    assert not v.allowed and "max open positions" in v.reason


def test_gross_exposure_cap_trims():
    held = {s: 19_000 for s in ["XLB", "XLE", "XLF", "XLI", "XLK"]}   # 95%
    v = check_order("XLU", 20_000, 100_000, held, 0, False)
    assert v.allowed and v.adjusted_notional == pytest.approx(5_000)
    assert "gross cap" in v.reason


def test_symbol_outside_universe_refused():
    v = check_order("TSLA", 1_000, 100_000, {}, 0, False)
    assert not v.allowed and "not in the traded universe" in v.reason


def test_daily_order_cap():
    v = check_order("XLK", 1_000, 100_000, {}, config.MAX_ORDERS_PER_DAY, False)
    assert not v.allowed and "daily order cap" in v.reason


def test_reducing_orders_always_allowed():
    """A book at its caps must still be able to shrink."""
    held = {s: 20_000 for s in ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP"]}
    v = check_order("XLB", -20_000, 100_000, held, 0, True)
    assert v.allowed


# ---- tier-2 emergency detection -------------------------------------------

def test_unknown_symbol_triggers_emergency():
    p = detect_emergency(100_000, {"XLK": 10_000, "GME": 5_000}, 1, 0)
    assert any("never chose" in x for x in p)


def test_stale_data_triggers_emergency():
    p = detect_emergency(100_000, {"XLK": 10_000}, 9, 0)
    assert any("stale" in x for x in p)


def test_exposure_breach_triggers_emergency():
    p = detect_emergency(100_000, {s: 30_000 for s in ["XLB", "XLE", "XLF", "XLK"]}, 1, 0)
    assert any("gross exposure" in x for x in p)
    assert any("position cap" in x for x in p)


def test_repeated_api_errors_trigger_emergency():
    p = detect_emergency(100_000, {}, 1, config.MAX_CONSECUTIVE_API_ERRORS)
    assert any("consecutive broker API errors" in x for x in p)


def test_broker_account_flags_trigger_emergency():
    p = detect_emergency(100_000, {}, 1, 0, account_flags=["trading_blocked"])
    assert any("trading_blocked" in x for x in p)


def test_healthy_state_is_clean():
    assert detect_emergency(100_000, {"XLK": 20_000, "XLE": 15_000}, 1, 0, []) == []


def test_zero_equity_triggers_emergency():
    assert detect_emergency(0, {}, 1, 0) != []


# ---- research/live data separation ----------------------------------------

def test_research_loader_refuses_live_market_cache():
    from engine.data import TestDataViolation, _guard
    import pandas as pd
    with pytest.raises(TestDataViolation, match="LIVE market cache"):
        _guard(pd.DataFrame(), "research/live/market_cache/SPY.csv")


def test_unknown_open_order_triggers_emergency():
    """A resting order for a symbol outside the book is a future unknown
    position. Catch it before it fills, not after."""
    p = detect_emergency(100_000, {"XLK": 10_000}, 1, 0,
                         open_order_symbols=["XLK", "NVDA"])
    assert any("outside the book" in x and "NVDA" in x for x in p)


def test_known_open_orders_are_fine():
    assert detect_emergency(100_000, {"XLK": 10_000}, 1, 0,
                            open_order_symbols=["XLK", "QQQ"]) == []


# ---- idempotency ----------------------------------------------------------

def test_pending_orders_count_as_committed_exposure():
    """Re-running the loop before fills must not re-submit the book.

    Regression: the first live run submitted 4 orders; running it again the
    same session submitted 4 MORE, because exposure was measured from filled
    positions only. Pending orders are committed exposure.
    """
    class FakeOrder:
        def __init__(self, sym, qty, side, filled=0):
            self.symbol, self.qty, self.filled_qty = sym, qty, filled
            self.side = type("S", (), {"value": side})()

    def pending_qty(orders):
        out = {}
        for o in orders:
            q = float(o.qty) - float(o.filled_qty)
            if o.side.value == "sell":
                q = -q
            out[o.symbol] = out.get(o.symbol, 0.0) + q
        return out

    pend = pending_qty([FakeOrder("XLK", 83, "buy"), FakeOrder("QQQ", 30, "buy")])
    assert pend == {"XLK": 83.0, "QQQ": 30.0}

    equity, px = 100_000.0, 183.0
    target_w = 0.1525
    current_w = (0.0 + pend["XLK"] * px) / equity      # position 0 + pending
    residual = abs(target_w - current_w) * equity
    # The only gap left is whole-share dust: less than one share, so it can
    # never round up to another order. Before the fix the "residual" was the
    # entire target and the book got submitted twice.
    assert residual < px
    assert int(residual // px) == 0


def test_partially_filled_order_leaves_only_the_remainder_pending():
    class FakeOrder:
        def __init__(self, sym, qty, side, filled):
            self.symbol, self.qty, self.filled_qty = sym, qty, filled
            self.side = type("S", (), {"value": side})()
    o = FakeOrder("XLI", 138, "buy", 100)
    remaining = float(o.qty) - float(o.filled_qty)
    assert remaining == 38.0


# ---- post-open reconciliation of expired OPG orders ------------------------
#
# Regression source: on 2026-08-24 every market-on-open order the book placed
# (XLE 313, XLI 138, XLK 83, QQQ 30) was EXPIRED by Alpaca at 09:32-09:34 ET
# with zero filled. OPG orders are auction-only; anything the opening auction
# does not execute is killed rather than left resting, so the account stayed
# flat all day while the strategy believed it held four positions.

from live.reconcile_open import plan_replacements  # noqa: E402


class ExpiredOrder:
    def __init__(self, sym, qty, side="buy", filled=0, oid=None):
        self.symbol, self.qty, self.filled_qty = sym, qty, filled
        self.side = type("S", (), {"value": side})()
        self.id = oid or f"id-{sym}"


def test_expired_opg_orders_are_replaced_as_whole_shares():
    plan = plan_replacements(
        [ExpiredOrder("XLE", 313), ExpiredOrder("QQQ", 30)], set(), {})
    assert [(r.symbol, r.side, r.qty) for r in plan] == \
           [("XLE", "buy", 313), ("QQQ", "buy", 30)]
    assert all("expired unfilled" in r.reason for r in plan)


def test_replacement_never_happens_twice_for_the_same_order():
    """Idempotency: a second run must be a no-op, not a doubled book."""
    expired = [ExpiredOrder("XLK", 83, oid="abc")]
    first = plan_replacements(expired, set(), {})
    assert len(first) == 1
    again = plan_replacements(expired, {"abc"}, {})
    assert again == []


def test_partial_fill_replaces_only_the_remainder():
    plan = plan_replacements([ExpiredOrder("XLI", 138, filled=100)], set(), {})
    assert (plan[0].symbol, plan[0].qty) == ("XLI", 38)


def test_live_resting_order_already_covers_the_exposure():
    """A resting order in the same direction is committed exposure already."""
    assert plan_replacements([ExpiredOrder("XLE", 313)], set(), {"XLE": 313.0}) == []


def test_partially_covered_expiry_replaces_only_the_gap():
    plan = plan_replacements([ExpiredOrder("XLE", 313)], set(), {"XLE": 100.0})
    assert (plan[0].symbol, plan[0].qty) == ("XLE", 213)


def test_opposite_direction_resting_order_does_not_cover_a_buy():
    """A resting SELL does not satisfy an expired BUY - netting it would flip
    the book's direction rather than restore the intended position."""
    plan = plan_replacements([ExpiredOrder("XLK", 83, "buy")], set(),
                             {"XLK": -50.0})
    assert (plan[0].side, plan[0].qty) == ("buy", 83)


def test_expired_sells_are_replaced_as_sells():
    plan = plan_replacements([ExpiredOrder("XLU", 40, "sell")], set(), {})
    assert (plan[0].side, plan[0].qty) == ("sell", 40)


def test_symbols_outside_the_universe_are_never_replaced():
    """Tier-2 owns unknown symbols. This script must not trade them at all."""
    assert plan_replacements([ExpiredOrder("NVDA", 1)], set(), {}) == []


def test_fully_filled_order_needs_no_replacement():
    assert plan_replacements([ExpiredOrder("QQQ", 30, filled=30)], set(), {}) == []


def test_replacement_window_closes_an_hour_after_the_open():
    """Under launchd a job missed while asleep runs on WAKE, so this script can
    fire hours after the auction it exists to repair. Filling then is a
    different trade at a different price."""
    from datetime import datetime as dt

    from live.reconcile_open import within_replacement_window
    assert within_replacement_window(dt(2026, 8, 24, 9, 40))
    assert within_replacement_window(dt(2026, 8, 24, 10, 30))   # edge of window
    assert not within_replacement_window(dt(2026, 8, 24, 10, 31))
    assert not within_replacement_window(dt(2026, 8, 24, 14, 0))
    assert not within_replacement_window(dt(2026, 8, 24, 9, 29))  # pre-auction
