"""Run IDEA-109 (unlevered) and IDEA-110 (SPY-vol levered) on 2001-2009 and
2010-2022. TEST (2023+) is NOT touched: it stays locked until the user says
the exact word UNLOCK.
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
from engine.metrics import buy_and_hold  # noqa: E402
from strategies.risklayer import make  # noqa: E402
from strategies.trend import SECTORS  # noqa: E402

LEDGER = RESEARCH / "VARIANT_LEDGER.md"
ERAS = {"2001-2009": ("2001-01-01", "2009-12-31"),
        "2010-2022": ("2010-01-01", "2022-12-31")}
TICKERS = SECTORS + ["QQQ", "SPY"]


def main():
    cache = {t: load(t) for t in TICKERS}
    n = 212
    rows = []
    for risk_pct in (0.005, 0.0075, 0.010):
        for levered in (False, True):
            idea = "IDEA-110" if levered else "IDEA-109"
            lbl = (f"risk={risk_pct:.2%}/trade, exit=2xATR20, cap25%/6pos/gross"
                   + ("SPYvol lev<=3x, financing on" if levered else "100%, 20% book vol"))
            strat = make(risk_pct, levered)
            for era, (s, e) in ERAS.items():
                n += 1
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
                with open(LEDGER, "a") as fh:
                    fh.write(f"[{n:04d}] {ts} | REGISTERED | {idea} | book: "
                             f"IDEA-066 sectors + IDEA-107 QQQ | {lbl} | {s}..{e} "
                             f"| pending | ADAPT: 2xATR20 exit-distance proxy (no "
                             f"published stop in either component)\n")
                res = run_backtest(strat, cache, name=f"{idea} {lbl}",
                                   start=s, end=e, benchmark_assets=["SPY"])
                st = res.stats
                rf = risk_free_daily(res.returns.index)
                spy_bh = buy_and_hold(cache["SPY"]["Open"].loc[res.returns.index]
                                      .to_frame("SPY"), rf, 2e-4)
                qqq_bh = buy_and_hold(cache["QQQ"]["Open"].loc[res.returns.index]
                                      .to_frame("QQQ"), rf, 2e-4)
                gross = res.positions.abs().sum(axis=1)
                flags = "; ".join(res.absurd)
                stress = ""
                if len(res.stress) > 1:
                    stress = (f" | 2x costs CAGR {res.stress[2.0]['cagr']:+.2%}"
                              f" 3x {res.stress[3.0]['cagr']:+.2%}")
                with open(LEDGER, "a") as fh:
                    fh.write(f"[{n:04d}] {ts} | RESULT | CAGR {st['cagr']:+.2%}, "
                             f"Sharpe {st['sharpe']:.2f}, maxDD {st['max_drawdown']:.1%}"
                             f" | vs SPY CAGR {spy_bh['cagr']:+.2%}/DD "
                             f"{spy_bh['max_drawdown']:.1%}, QQQ CAGR {qqq_bh['cagr']:+.2%}"
                             f"/DD {qqq_bh['max_drawdown']:.1%} | {res.verdict} | "
                             f"mean gross {gross.mean():.2f}x, max {gross.max():.2f}x"
                             f"{stress}" + (f" | FLAGS: {flags}" if flags else "") + "\n")
                rows.append(dict(variant=n, idea=idea, risk_pct=risk_pct,
                                 levered=levered, era=era, cagr=st["cagr"],
                                 sharpe=st["sharpe"], max_dd=st["max_drawdown"],
                                 total_return=st["total_return"],
                                 ann_vol=st["ann_vol"],
                                 mean_gross=gross.mean(), max_gross=gross.max(),
                                 spy_cagr=spy_bh["cagr"], spy_dd=spy_bh["max_drawdown"],
                                 qqq_cagr=qqq_bh["cagr"], qqq_dd=qqq_bh["max_drawdown"],
                                 cagr_2x=res.stress.get(2.0, {}).get("cagr"),
                                 cagr_3x=res.stress.get(3.0, {}).get("cagr"),
                                 verdict=res.verdict, flags=flags))
                print(f"[{n:04d}] {idea} risk={risk_pct:.2%} lev={levered} {era}: "
                      f"CAGR {st['cagr']:+.2%} Sh {st['sharpe']:.2f} DD "
                      f"{st['max_drawdown']:.1%} vol {st['ann_vol']:.1%} "
                      f"gross {gross.mean():.2f}x -> {res.verdict}")
    df = pd.DataFrame(rows)
    df.to_csv(RESEARCH / "results" / "risk_layer.csv", index=False)
    print(f"\nSaved {len(df)} rows. TEST WINDOW NOT TOUCHED (locked).")


if __name__ == "__main__":
    main()
