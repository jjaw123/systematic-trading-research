"""Per-sleeve P&L attribution for the deployed book.

The live book (`strategies/risklayer.py`) blends two components that trade
DISJOINT symbols:

  * ``sector_rotation_6m``  -> the nine sector ETFs (``config.SECTORS``)
  * ``vol_target_qqq``      -> QQQ only

so every symbol the book can hold belongs to exactly one sleeve and a day's
P&L splits cleanly between them.

Attribution is REALIZED, not modelled: a symbol's dollar P&L for the day is
yesterday's position value times its close-to-close price move. The sleeve
totals plus a residual (``unattributed`` -- fees, slippage, execution timing,
cash drift, any symbol we lack a price for) reconcile to the book's actual
equity change. The residual is reported, never hidden -- if it is large the
sleeve numbers are not to be trusted that day.
"""

import csv
import json
from pathlib import Path

from live.config import SECTORS, TRADED_UNIVERSE

SLEEVES = {
    "sector_rotation_6m": tuple(SECTORS),
    "vol_target_qqq": tuple(s for s in TRADED_UNIVERSE if s not in SECTORS),
}

_SYMBOL_SLEEVE = {sym: name for name, syms in SLEEVES.items() for sym in syms}

# Fail loudly at import if the deployed universe ever grows a symbol no sleeve
# claims. Silent mis-attribution is worse than a crash on deploy.
_unmapped = [s for s in TRADED_UNIVERSE if s not in _SYMBOL_SLEEVE]
if _unmapped:
    raise RuntimeError(
        f"attribution: no sleeve owns {_unmapped}. Update SLEEVES in "
        f"live/attribution.py when the deployed book changes.")

STRATEGY_RETURNS_COLUMNS = ["date", "sleeve", "pnl_dollars",
                            "return_on_prev_value", "prev_value"]


def sleeve_of(symbol):
    """Which component owns this symbol, or None if the book never holds it."""
    return _SYMBOL_SLEEVE.get(symbol)


def attribute(prev_values, prev_marks, cur_marks, equity_change):
    """Split a day's P&L across sleeves.

    prev_values   symbol -> signed position market value at yesterday's close
    prev_marks    symbol -> yesterday's close price
    cur_marks     symbol -> today's close price
    equity_change today's book equity minus yesterday's -- the figure the
                  sleeve totals plus the residual must sum to

    Returns ``{sleeve: {pnl_dollars, return_on_prev_value, prev_value}}`` for
    each sleeve, plus ``"unattributed": {"pnl_dollars": <residual>}``.
    A symbol missing from either mark dict contributes 0 P&L (its move lands
    in the residual) but still counts toward its sleeve's prior value.
    """
    agg = {name: {"pnl": 0.0, "prev_value": 0.0} for name in SLEEVES}
    for sym, pv in prev_values.items():
        name = _SYMBOL_SLEEVE.get(sym)
        if name is None:
            continue                      # tier-2 owns unknown symbols, not us
        pv = float(pv)
        agg[name]["prev_value"] += pv
        p0 = prev_marks.get(sym)
        p1 = cur_marks.get(sym)
        if p0 and p1:
            agg[name]["pnl"] += pv * (float(p1) / float(p0) - 1.0)

    out = {}
    modelled_total = 0.0
    for name, d in agg.items():
        pnl, pv = d["pnl"], d["prev_value"]
        modelled_total += pnl
        out[name] = {
            "pnl_dollars": round(pnl, 2),
            "return_on_prev_value": round(pnl / pv, 6) if pv else 0.0,
            "prev_value": round(pv, 2),
        }
    out["unattributed"] = {
        "pnl_dollars": round(float(equity_change) - modelled_total, 2)}
    return out


def append_rows(path, as_of, result):
    """Append one row per sleeve plus a residual row to strategy_returns.csv."""
    path = Path(path)
    write_header = not path.exists()
    with open(path, "a", newline="") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(STRATEGY_RETURNS_COLUMNS)
        for name in SLEEVES:
            d = result[name]
            w.writerow([as_of, name, d["pnl_dollars"],
                        d["return_on_prev_value"], d["prev_value"]])
        w.writerow([as_of, "unattributed",
                    result["unattributed"]["pnl_dollars"], "", ""])


def read_state(path):
    """Prior run's marks and position values, or None if absent/unreadable."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def write_state(path, as_of, marks, values):
    """Persist today's closes and position values for tomorrow's attribution."""
    Path(path).write_text(json.dumps({
        "as_of": str(as_of),
        "marks": {k: round(float(v), 6) for k, v in marks.items()},
        "values": {k: round(float(v), 2) for k, v in values.items()},
    }, indent=2, default=str))
