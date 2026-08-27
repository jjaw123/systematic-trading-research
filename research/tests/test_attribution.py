"""Per-sleeve P&L attribution for the deployed book.

The live book blends two components that trade DISJOINT symbols, so a day's
P&L must split cleanly between them and reconcile (via a residual) to the
book's actual equity change.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import attribution  # noqa: E402
from live.config import SECTORS, TRADED_UNIVERSE  # noqa: E402


def test_every_traded_symbol_maps_to_exactly_one_sleeve():
    seen = [s for syms in attribution.SLEEVES.values() for s in syms]
    assert sorted(seen) == sorted(TRADED_UNIVERSE)
    assert len(seen) == len(set(seen))               # no symbol in two sleeves
    for s in TRADED_UNIVERSE:
        assert attribution.sleeve_of(s) in attribution.SLEEVES


def test_sleeves_match_the_deployed_components():
    assert set(attribution.SLEEVES["sector_rotation_6m"]) == set(SECTORS)
    assert set(attribution.SLEEVES["vol_target_qqq"]) == {"QQQ"}


def test_pnl_splits_by_sleeve_from_realized_price_moves():
    prev_values = {"XLK": 10_000.0, "XLE": 5_000.0, "QQQ": 8_000.0}
    prev_marks = {"XLK": 100.0, "XLE": 50.0, "QQQ": 400.0}
    cur_marks = {"XLK": 110.0, "XLE": 49.0, "QQQ": 404.0}   # +10%, -2%, +1%

    # book equity moved by exactly the sum of the position moves (no residual)
    equity_change = 1000.0 - 100.0 + 80.0
    res = attribution.attribute(prev_values, prev_marks, cur_marks, equity_change)

    assert res["sector_rotation_6m"]["pnl_dollars"] == pytest.approx(900.0)
    assert res["sector_rotation_6m"]["prev_value"] == pytest.approx(15_000.0)
    assert res["sector_rotation_6m"]["return_on_prev_value"] == pytest.approx(0.06)
    assert res["vol_target_qqq"]["pnl_dollars"] == pytest.approx(80.0)
    assert res["vol_target_qqq"]["return_on_prev_value"] == pytest.approx(0.01)
    assert res["unattributed"]["pnl_dollars"] == pytest.approx(0.0)


def test_residual_absorbs_fees_slippage_and_cash_drift():
    prev_values = {"XLK": 10_000.0}
    prev_marks = {"XLK": 100.0}
    cur_marks = {"XLK": 101.0}                     # modelled move: +100
    res = attribution.attribute(prev_values, prev_marks, cur_marks,
                                equity_change=88.0)   # book only gained 88
    assert res["sector_rotation_6m"]["pnl_dollars"] == pytest.approx(100.0)
    assert res["unattributed"]["pnl_dollars"] == pytest.approx(-12.0)


def test_missing_price_leaves_that_symbols_move_in_the_residual():
    prev_values = {"QQQ": 8_000.0}
    res = attribution.attribute(prev_values, prev_marks={}, cur_marks={},
                                equity_change=25.0)
    assert res["vol_target_qqq"]["pnl_dollars"] == pytest.approx(0.0)
    assert res["vol_target_qqq"]["prev_value"] == pytest.approx(8_000.0)
    assert res["unattributed"]["pnl_dollars"] == pytest.approx(25.0)


def test_flat_book_attributes_nothing_and_still_reconciles():
    res = attribution.attribute({}, {}, {}, equity_change=-3.0)
    assert res["sector_rotation_6m"]["pnl_dollars"] == 0.0
    assert res["vol_target_qqq"]["pnl_dollars"] == 0.0
    assert res["unattributed"]["pnl_dollars"] == pytest.approx(-3.0)


def test_symbols_outside_the_book_are_ignored_not_attributed():
    res = attribution.attribute({"NVDA": 9_999.0}, {"NVDA": 1.0},
                                {"NVDA": 2.0}, equity_change=0.0)
    assert res["sector_rotation_6m"]["prev_value"] == 0.0
    assert res["vol_target_qqq"]["prev_value"] == 0.0
    # NVDA's move is not modelled, so it all lands in the residual
    assert res["unattributed"]["pnl_dollars"] == pytest.approx(0.0)


def test_append_rows_writes_one_row_per_sleeve_plus_residual(tmp_path):
    res = attribution.attribute(
        {"XLK": 10_000.0, "QQQ": 8_000.0},
        {"XLK": 100.0, "QQQ": 400.0}, {"XLK": 101.0, "QQQ": 400.0},
        equity_change=100.0)
    path = tmp_path / "strategy_returns.csv"
    attribution.append_rows(path, "2026-08-27", res)
    attribution.append_rows(path, "2026-08-28", res)

    lines = path.read_text().strip().splitlines()
    assert lines[0] == "date,sleeve,pnl_dollars,return_on_prev_value,prev_value"
    # header + 3 rows/day * 2 days
    assert len(lines) == 1 + 6
    assert lines[1].startswith("2026-08-27,sector_rotation_6m,")
    assert ",unattributed," in lines[3]


def test_state_round_trips_and_missing_file_is_none(tmp_path):
    path = tmp_path / "attribution_state.json"
    assert attribution.read_state(path) is None
    attribution.write_state(path, "2026-08-27", {"XLK": 101.0}, {"XLK": 9_900.0})
    st = attribution.read_state(path)
    assert st["as_of"] == "2026-08-27"
    assert st["marks"]["XLK"] == pytest.approx(101.0)
    assert st["values"]["XLK"] == pytest.approx(9_900.0)


def test_corrupt_state_file_reads_as_none(tmp_path):
    path = tmp_path / "attribution_state.json"
    path.write_text("{ not json")
    assert attribution.read_state(path) is None
