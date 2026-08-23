"""Full TRAIN-window sweep of every runnable idea in research/IDEA_LOG.md.

Protocol per research/VARIANT_LEDGER.md: every variant gets a REGISTERED line
in the ledger BEFORE its backtest runs; a RESULT line is appended after.
Ledger lines are append-only. Results table saved to research/results/.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

RESEARCH = Path(__file__).resolve().parent.parent / "research"
sys.path.insert(0, str(RESEARCH))

from engine import LookaheadError, TestDataViolation, load, run_backtest  # noqa: E402
from strategies.registry import all_entries  # noqa: E402

LEDGER = RESEARCH / "VARIANT_LEDGER.md"
RESULTS_DIR = RESEARCH / "results"


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z EDT").replace(" EDT EDT", " EDT")


def append_ledger(line):
    with open(LEDGER, "a") as fh:
        fh.write(line + "\n")


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    entries = all_entries()
    tickers = sorted({t for e in entries for t in e["tickers"]})
    cache = {t: load(t) for t in tickers}
    print(f"{len(entries)} variants across {len(tickers)} tickers loaded.")

    rows = []
    for n, e in enumerate(entries, start=1):
        vid = f"[{n:04d}]"
        settings = e["settings"] + (f" | ADAPT: {e['adapt']}" if e["adapt"] else "")
        append_ledger(f"{vid} {ts()} | REGISTERED | {e['idea']} | {e['asset']} | "
                      f"{settings} | 2010-01-01..2022-12-31 | pending")
        data = (cache[e["tickers"][0]] if len(e["tickers"]) == 1
                else {t: cache[t] for t in e["tickers"]})
        t0 = time.time()
        try:
            res = run_backtest(e["build"], data, name=f"{e['idea']} {e['name']} [{e['asset']}]",
                               benchmark_assets=e["bench"])
            s, b = res.stats, res.benchmark_stats
            flags = "; ".join(res.absurd) if res.absurd else ""
            stress_txt = ""
            if len(res.stress) > 1:
                stress_txt = (f" | 2x: {res.stress[2.0]['total_return']:+.1%}"
                              f" 3x: {res.stress[3.0]['total_return']:+.1%}")
            append_ledger(
                f"{vid} {ts()} | RESULT | return {s['total_return']:+.1%} vs B&H "
                f"{b['total_return']:+.1%} | maxDD {s['max_drawdown']:.1%} vs B&H "
                f"{b['max_drawdown']:.1%} | {res.verdict} | Sharpe {s['sharpe']:.2f}, "
                f"trades/yr {res.trades_per_year:.1f}{stress_txt}"
                + (f" | FLAGS: {flags}" if flags else ""))
            rows.append(dict(
                variant=n, idea=e["idea"], name=e["name"], asset=e["asset"],
                trades_per_yr=round(res.trades_per_year, 1),
                total_return=s["total_return"], cagr=s["cagr"],
                sharpe=s["sharpe"], max_dd=s["max_drawdown"],
                bh_return=b["total_return"], bh_max_dd=b["max_drawdown"],
                ret_2x=res.stress.get(2.0, {}).get("total_return"),
                ret_3x=res.stress.get(3.0, {}).get("total_return"),
                verdict=res.verdict, flags=flags,
            ))
            print(f"{vid} {e['idea']} {e['name']} [{e['asset']}]: "
                  f"{s['total_return']:+.1%} Sharpe {s['sharpe']:.2f} "
                  f"DD {s['max_drawdown']:.1%} -> {res.verdict}"
                  f" ({time.time()-t0:.1f}s)")
        except (LookaheadError, TestDataViolation) as ex:
            append_ledger(f"{vid} {ts()} | RESULT | ERROR ({type(ex).__name__}): {ex}")
            rows.append(dict(variant=n, idea=e["idea"], name=e["name"],
                             asset=e["asset"], verdict=f"ERROR {type(ex).__name__}",
                             flags=str(ex)[:120]))
            print(f"{vid} {e['idea']} {e['name']}: {type(ex).__name__}: {ex}")
        except Exception as ex:  # noqa: BLE001
            append_ledger(f"{vid} {ts()} | RESULT | ERROR ({type(ex).__name__}): {ex}")
            rows.append(dict(variant=n, idea=e["idea"], name=e["name"],
                             asset=e["asset"], verdict="ERROR", flags=str(ex)[:120]))
            print(f"{vid} {e['idea']} {e['name']}: ERROR {type(ex).__name__}: {ex}")

    df = pd.DataFrame(rows)
    out = RESULTS_DIR / "train_sweep_2026-08-23.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} rows -> {out}")
    ok = df[~df["verdict"].astype(str).str.startswith("ERROR")]
    print(f"PASS: {(ok['verdict'] == 'PASS').sum()} | FAIL: {(ok['verdict'] == 'FAIL').sum()} "
          f"| WITHHELD/absurd: {ok['verdict'].str.startswith('WITHHELD').sum()} "
          f"| errors: {len(df) - len(ok)}")


if __name__ == "__main__":
    main()
