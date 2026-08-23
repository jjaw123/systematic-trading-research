"""Weekly paper-trading report: live vs backtest expectation + shutoff checks.

    python research/live/weekly_report.py

Writes research/live/reports/weekly_YYYY-MM-DD.md and prints a summary.
Expectation bands come from the REGISTERED backtest variants, not from
anything recomputed here, so the comparison is against what was actually
recorded before going live.
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import journal  # noqa: E402
from live.config import LIVE_RETURNS_PATH, RISK_PCT_PER_TRADE  # noqa: E402
from live.halt import load_rules, read_state  # noqa: E402
from live.daily_loop import emergency_active  # noqa: E402

REPORTS = Path(__file__).resolve().parent / "reports"
TRADING_DAYS = 252

# Recorded backtest expectations for the DEPLOYED config
# (IDEA-109 unlevered risk layer @0.75%/trade, ledger variants [0217]/[0218]).
EXPECTATION = {
    "config": "IDEA-109 unlevered risk layer @0.75%/trade",
    "variants": "[0217] 2001-2009, [0218] 2010-2022",
    "eras": {
        "2001-2009": {"cagr": 0.0287, "sharpe": 0.11, "max_dd": -0.333,
                      "ann_vol": 0.138},
        "2010-2022": {"cagr": 0.1094, "sharpe": 0.80, "max_dd": -0.156,
                      "ann_vol": 0.134},
    },
}


def _live():
    if not LIVE_RETURNS_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(LIVE_RETURNS_PATH, index_col=0, parse_dates=True).sort_index()


def _stats(r):
    r = r.dropna()
    if len(r) < 2:
        return None
    eq = (1 + r).cumprod()
    years = len(r) / TRADING_DAYS
    vol = r.std(ddof=0) * np.sqrt(TRADING_DAYS)
    return {"days": len(r), "total": eq.iloc[-1] - 1,
            "cagr": eq.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan,
            "ann_vol": vol,
            "sharpe": (r.mean() / r.std(ddof=0) * np.sqrt(TRADING_DAYS))
            if r.std(ddof=0) > 0 else np.nan,
            "max_dd": (eq / eq.cummax() - 1).min()}


def _expectation_band(days):
    """Where should live sit if the backtest era range is the truth?

    Uses the two recorded eras as the plausible range, and scales the
    volatility band by sqrt(time) - a week of data cannot confirm or refute
    an annual CAGR, and the report says so rather than pretending otherwise.
    """
    lo, hi = EXPECTATION["eras"]["2001-2009"], EXPECTATION["eras"]["2010-2022"]
    yrs = days / TRADING_DAYS
    band = {}
    for name, e in (("bear-era 2001-2009", lo), ("bull-era 2010-2022", hi)):
        exp_ret = (1 + e["cagr"]) ** yrs - 1
        sd = e["ann_vol"] * np.sqrt(yrs)
        band[name] = {"expected_return": exp_ret,
                      "one_sd": sd,
                      "range_1sd": (exp_ret - sd, exp_ret + sd)}
    return band


def _reconcile(records, since):
    """decisions -> orders -> fills, plus anything the limits layer refused."""
    recent = [r for r in records if str(r.get("as_of", "")) >= str(since)]
    kinds = {k: [r for r in recent if r["kind"] == k]
             for k in ("decision", "order", "fill", "rejected", "event")}
    crit = [r for r in kinds["event"] if r.get("severity") in ("critical", "error")]
    return kinds, crit


def build():
    REPORTS.mkdir(exist_ok=True)
    today = date.today()
    since = today - pd.Timedelta(days=7)
    live = _live()
    records = journal.read_all()
    kinds, crit = _reconcile(records, since.date() if hasattr(since, "date") else since)

    L = []
    A = L.append
    A(f"# Weekly paper report — {today}")
    A("")
    A(f"*Mode: **PAPER ONLY**. Config: {EXPECTATION['config']} "
      f"(backtest variants {EXPECTATION['variants']}).*")
    A("")

    # ---- live performance ------------------------------------------------
    A("## 1. Live results")
    A("")
    if live.empty or len(live) < 2:
        n = len(live)
        A(f"Only **{n} session{'s' if n != 1 else ''}** of live history so far. "
          f"No return statistics yet — a Sharpe or drawdown computed from this "
          f"would be noise dressed up as a number.")
        if not live.empty:
            A("")
            A(f"- Current equity: **${live['equity'].iloc[-1]:,.2f}**")
            A(f"- Gross exposure: **{live['gross_exposure'].iloc[-1]:.1%}**")
        stats = None
    else:
        stats = _stats(live["net_return"])
        wk = live["net_return"].iloc[-5:]
        A(f"- Equity: **${live['equity'].iloc[-1]:,.2f}** "
          f"(started ${live['equity'].iloc[0]:,.2f})")
        A(f"- This week: **{(1 + wk).prod() - 1:+.2%}**")
        A(f"- Since inception ({stats['days']} sessions): "
          f"**{stats['total']:+.2%}**, ann. vol {stats['ann_vol']:.1%}, "
          f"Sharpe {stats['sharpe']:.2f}, max DD {stats['max_dd']:.1%}")
        A(f"- Gross exposure now: **{live['gross_exposure'].iloc[-1]:.1%}**")
    A("")

    # ---- vs backtest -----------------------------------------------------
    A("## 2. Live vs backtest expectation")
    A("")
    A("| Era (recorded) | CAGR | Sharpe | Max DD | Ann vol |")
    A("|---|---|---|---|---|")
    for name, e in EXPECTATION["eras"].items():
        A(f"| {name} | {e['cagr']:+.2%} | {e['sharpe']:.2f} | "
          f"{e['max_dd']:.1%} | {e['ann_vol']:.1%} |")
    A("")
    if stats:
        band = _expectation_band(stats["days"])
        A(f"Over {stats['days']} sessions, live returned **{stats['total']:+.2%}**. "
          f"Expectation ranges (±1 sd, scaled by √time):")
        A("")
        for name, b in band.items():
            lo, hi = b["range_1sd"]
            inside = lo <= stats["total"] <= hi
            A(f"- {name}: {b['expected_return']:+.2%} "
              f"(1sd band {lo:+.2%} to {hi:+.2%}) — live is "
              f"**{'inside' if inside else 'OUTSIDE'}** this band")
        A("")
        A("> A sample this short cannot distinguish these eras. Treat a band "
          "breach as a prompt to look at execution, not as evidence about edge.")
    else:
        A("*Not enough live history to compare. This section fills in once "
          "there are at least a few sessions.*")
    A("")

    # ---- shutoff rules ---------------------------------------------------
    A("## 3. Shutoff rule checks")
    A("")
    try:
        cfg, sha = load_rules()
        rev = cfg.get("meta", {}).get("revision", "?")
        A(f"Rules file: revision **{rev}**, sha256 `{sha[:16]}…`")
        A("")
        d = cfg["drawdown_test"]
        worst = d["worst_backtest_drawdown"]
        A(f"**Tier 1 — drawdown.** Warn at {-worst * d['warn_multiple']:.1%}, "
          f"halt at {-worst * d['halt_multiple']:.1%} "
          f"({d['halt_multiple']}× the recorded backtest worst of {-worst:.1%}).")
        if stats:
            A(f"Live drawdown is **{stats['max_dd']:.1%}**.")
        A("")
        s = cfg["skill_test"]
        A(f"**Tier 1 — skill vs random entries.** Windows {s['windows']}d, "
          f"floor {s['percentile_floor']}th percentile, "
          f"needs {s['min_live_days']} sessions before it evaluates.")
        have = len(live)
        if have < s["min_live_days"]:
            A(f"Currently **{have}/{s['min_live_days']}** sessions — not yet "
              f"evaluated, by design.")
    except Exception as ex:  # noqa: BLE001
        A(f"**RULES FILE UNREADABLE — system fails closed: {ex}**")
    A("")
    st = read_state()
    A(f"**Tier 1 state:** {'HALTED — ' + str(st.get('reasons')) if st.get('halted') else 'not halted'}")
    em, why = emergency_active()
    A(f"**Tier 2 state:** {'EMERGENCY HALT — ' + why if em else 'clear'}")
    A("")

    # ---- execution reconciliation ---------------------------------------
    A("## 4. Execution (last 7 days)")
    A("")
    A(f"- Decisions logged: **{len(kinds['decision'])}**")
    A(f"- Orders submitted: **{len(kinds['order'])}**")
    A(f"- Fills recorded: **{len(kinds['fill'])}**")
    A(f"- Orders refused by the limits layer: **{len(kinds['rejected'])}**")
    if kinds["rejected"]:
        A("")
        for r in kinds["rejected"][-10:]:
            A(f"  - `{r['as_of']}` {r.get('symbol','?')}: {r.get('reason','')}")
    if kinds["order"]:
        A("")
        A("| Date | Symbol | Side | Qty | Notional | Reason |")
        A("|---|---|---|---|---|---|")
        for o in kinds["order"][-15:]:
            A(f"| {o['as_of']} | {o['symbol']} | {o['side']} | {o['qty']:.0f} | "
              f"${o['notional']:,.0f} | {str(o.get('reason',''))[:60]} |")
    if crit:
        A("")
        A("### Errors and critical events")
        for c in crit[-10:]:
            A(f"- `{c['as_of']}` **{c['what']}**: {str(c.get('detail'))[:160]}")
    A("")
    A("---")
    A(f"*Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
      f"No real money is at risk; REAL_MONEY_ENABLED is False.*")

    text = "\n".join(L)
    out = REPORTS / f"weekly_{today}.md"
    out.write_text(text)
    return out, text


if __name__ == "__main__":
    path, text = build()
    print(text)
    print(f"\n[saved] {path}")
