"""Era-robustness + parameter-neighborhood check for the sector-momentum family
(IDEA-004 / IDEA-066 / IDEA-102), the only genuine train-window passes.

Grid: formation {126,189,252}d x skip {0,21}d x topN {1,2,3} x weight {EW,IV}
Eras: 2000-01-01..2009-12-31 and 2010-01-01..2022-12-31 (TEST stays locked).
Every setting x era is registered in the variant ledger before it runs.
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH = Path(__file__).resolve().parent.parent / "research"
sys.path.insert(0, str(RESEARCH))

from engine import load, run_backtest  # noqa: E402
from strategies.common import CAL  # noqa: E402

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
LEDGER = RESEARCH / "VARIANT_LEDGER.md"
ERAS = {"2000-2009": ("2000-01-01", "2009-12-31"),
        "2010-2022": ("2010-01-01", "2022-12-31")}


def make_strategy(formation, skip, topn, weighting):
    def f(data):
        closes = pd.DataFrame({t: data[t]["Close"] for t in SECTORS}).dropna()
        r = closes.shift(skip) / closes.shift(skip + formation) - 1
        rank = r.rank(axis=1, ascending=False)
        sel = (rank <= topn).astype(float)
        if weighting == "IV":
            iv = 1.0 / closes.pct_change().rolling(20).std(ddof=0)
            sel = sel * iv
        w = sel.div(sel.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
        w[r.isna().any(axis=1)] = 0.0
        f_ = CAL["month_end"].reindex(closes.index).fillna(False)
        return w.where(f_).ffill().fillna(0.0)
    return f


def main():
    cache = {t: load(t) for t in SECTORS}
    n = 117
    rows = []
    for formation in (126, 189, 252):
        for skip in (0, 21):
            for topn in (1, 2, 3):
                for weighting in ("EW", "IV"):
                    strat = make_strategy(formation, skip, topn, weighting)
                    label = f"form={formation}d skip={skip}d top{topn} {weighting}"
                    for era, (start, end) in ERAS.items():
                        n += 1
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
                        with open(LEDGER, "a") as fh:
                            fh.write(f"[{n:04d}] {ts} | REGISTERED | IDEA-004+066+102 "
                                     f"| 9 SPDR sectors | {label}, monthly, EW bench "
                                     f"| {start}..{end} | pending (neighborhood/era check)\n")
                        try:
                            res = run_backtest(strat, cache, name=label,
                                               start=start, end=end)
                            s, b = res.stats, res.benchmark_stats
                            flags = "; ".join(res.absurd)
                            with open(LEDGER, "a") as fh:
                                fh.write(f"[{n:04d}] {ts} | RESULT | return "
                                         f"{s['total_return']:+.1%} vs B&H {b['total_return']:+.1%} "
                                         f"| maxDD {s['max_drawdown']:.1%} vs B&H "
                                         f"{b['max_drawdown']:.1%} | {res.verdict} | Sharpe "
                                         f"{s['sharpe']:.2f}, trades/yr {res.trades_per_year:.1f}"
                                         + (f" | FLAGS: {flags}" if flags else "") + "\n")
                            rows.append(dict(variant=n, formation=formation, skip=skip,
                                             topn=topn, weighting=weighting, era=era,
                                             total_return=s["total_return"], cagr=s["cagr"],
                                             sharpe=s["sharpe"], max_dd=s["max_drawdown"],
                                             bh_return=b["total_return"],
                                             bh_max_dd=b["max_drawdown"],
                                             trades_per_yr=res.trades_per_year,
                                             verdict=res.verdict, flags=flags))
                            print(f"[{n:04d}] {label} {era}: {s['total_return']:+.1%} "
                                  f"Sh {s['sharpe']:.2f} DD {s['max_drawdown']:.1%} -> {res.verdict}")
                        except Exception as ex:  # noqa: BLE001
                            with open(LEDGER, "a") as fh:
                                fh.write(f"[{n:04d}] {ts} | RESULT | ERROR "
                                         f"({type(ex).__name__}): {ex}\n")
                            print(f"[{n:04d}] {label} {era}: ERROR {ex}")
    df = pd.DataFrame(rows)
    out = RESEARCH / "results" / "sector_momentum_neighborhood.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
