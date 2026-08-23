"""Run IDEA-103/104/105/107 on TRAIN, then build the IDEA-108 survivor blend.

Survivors = strategies with a live KEEP/PASS status on train: IDEA-066 (kept
after era checks) plus any of the new four that PASS. Blend: monthly
inverse-vol (trailing 63d) weights on the survivors' net daily return streams.
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH = Path(__file__).resolve().parent.parent / "research"
sys.path.insert(0, str(RESEARCH))

from engine import load, run_backtest  # noqa: E402
from engine.data import risk_free_daily  # noqa: E402
from engine.metrics import buy_and_hold, summarize  # noqa: E402
from strategies.common import CAL  # noqa: E402
from strategies.external import entries  # noqa: E402
from strategies.trend import sector_rotation_6m  # noqa: E402

LEDGER = RESEARCH / "VARIANT_LEDGER.md"


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")


def led(line):
    with open(LEDGER, "a") as fh:
        fh.write(line + "\n")


def run_entry(n, e, cache):
    settings = e["settings"] + (f" | ADAPT: {e['adapt']}" if e["adapt"] else "")
    led(f"[{n:04d}] {ts()} | REGISTERED | {e['idea']} | {e['asset']} | {settings} "
        f"| 2010-01-01..2022-12-31 | pending")
    data = (cache[e["tickers"][0]] if len(e["tickers"]) == 1
            else {t: cache[t] for t in e["tickers"]})
    res = run_backtest(e["build"], data, name=e["idea"], benchmark_assets=e["bench"])
    s, b = res.stats, res.benchmark_stats
    flags = "; ".join(res.absurd)
    stress = ""
    if len(res.stress) > 1:
        stress = (f" | 2x: {res.stress[2.0]['total_return']:+.1%} "
                  f"3x: {res.stress[3.0]['total_return']:+.1%}")
    led(f"[{n:04d}] {ts()} | RESULT | return {s['total_return']:+.1%} vs B&H "
        f"{b['total_return']:+.1%} | maxDD {s['max_drawdown']:.1%} vs B&H "
        f"{b['max_drawdown']:.1%} | {res.verdict} | Sharpe {s['sharpe']:.2f}, "
        f"trades/yr {res.trades_per_year:.1f}{stress}"
        + (f" | FLAGS: {flags}" if flags else ""))
    print(f"[{n:04d}] {e['idea']} {e['name']}: {s['total_return']:+.1%} "
          f"CAGR {s['cagr']:+.2%} Sh {s['sharpe']:.2f} DD {s['max_drawdown']:.1%} "
          f"vs B&H {b['total_return']:+.1%}/{b['max_drawdown']:.1%} -> {res.verdict}"
          + (f" FLAGS: {flags}" if flags else ""))
    return res


def main():
    ext = entries()
    tickers = sorted({t for e in ext for t in e["tickers"]}
                     | {"XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"})
    cache = {t: load(t) for t in tickers}

    n = 189
    results = {}
    for e in ext:
        n += 1
        results[e["idea"]] = (e, run_entry(n, e, cache))

    # IDEA-066 (kept): reproduce registered variant [0042] for its return stream.
    sectors = {t: cache[t] for t in
               ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")}
    r66 = run_backtest(sector_rotation_6m, sectors, name="IDEA-066 (repro of [0042])")
    print(f"IDEA-066 repro: {r66.stats['total_return']:+.1%} -> {r66.verdict}")

    streams = {"IDEA-066": r66.returns}
    for idea, (e, res) in results.items():
        if res.verdict == "PASS":
            streams[idea] = res.returns
    survivors = list(streams)
    print("\nSurvivors for blend:", survivors)

    rets = pd.DataFrame(streams).dropna()
    print("\n=== correlation matrix of daily net returns (train) ===")
    print(rets.corr().round(2).to_string())

    n += 1
    led(f"[{n:04d}] {ts()} | REGISTERED | IDEA-108 | blend of {'+'.join(survivors)} "
        f"| inverse-vol (63d) monthly, no tuning | 2010-01-01..2022-12-31 | pending")
    iv = 1.0 / rets.rolling(63).std(ddof=0)
    f = CAL["month_end"].reindex(rets.index).fillna(False)
    w = iv.copy()
    w[~f.values] = np.nan                              # sample at month-ends only
    w = w.div(w.sum(axis=1), axis=0).ffill().shift(1)  # applied from next day
    w = w.fillna(1.0 / len(rets.columns))
    blend = (w * rets).sum(axis=1)
    rf = risk_free_daily(rets.index)
    bstats = summarize(blend, rf)

    spy_open = cache["SPY"]["Open"].loc[rets.index]
    qqq_open = cache["QQQ"]["Open"].loc[rets.index]
    spy_bh = buy_and_hold(spy_open.to_frame("SPY"), rf, 2e-4)
    qqq_bh = buy_and_hold(qqq_open.to_frame("QQQ"), rf, 2e-4)

    led(f"[{n:04d}] {ts()} | RESULT | CAGR {bstats['cagr']:+.2%}, Sharpe "
        f"{bstats['sharpe']:.2f}, maxDD {bstats['max_drawdown']:.1%} | vs SPY CAGR "
        f"{spy_bh['cagr']:+.2%}/DD {spy_bh['max_drawdown']:.1%}, QQQ CAGR "
        f"{qqq_bh['cagr']:+.2%}/DD {qqq_bh['max_drawdown']:.1%} | components: "
        f"{'+'.join(survivors)} | reallocation costs between strategies not modeled")

    print("\n=== IDEA-108 blend vs benchmarks (2010-2022) ===")
    for name, st in (("BLEND", bstats), ("SPY B&H", spy_bh), ("QQQ B&H", qqq_bh)):
        print(f"{name:8s} CAGR {st['cagr']:+.2%} | Sharpe {st['sharpe']:.2f} | "
              f"maxDD {st['max_drawdown']:.1%} | total {st['total_return']:+.1%}")

    pd.DataFrame({"blend": blend}).to_csv(RESEARCH / "results" / "blend_returns.csv")


if __name__ == "__main__":
    main()
