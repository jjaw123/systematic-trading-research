# Systematic Trading Research

A disciplined backtesting and paper-trading system for daily-bar ETF, equity,
and gold strategies. Built around one idea: **make it hard to fool yourself.**

> **Proprietary — All Rights Reserved.** See [LICENSE](LICENSE). Viewing this
> repository grants no right to copy, reuse, or adapt any part of it.
> Nothing here is investment advice.

---

## The protocol

Every result in this repo was produced under rules fixed *before* testing began.

**Nothing is tested until it is written down and counted.** Every idea is logged
in [`research/IDEA_LOG.md`](research/IDEA_LOG.md) with a timestamp, the exact
rule, allowed settings, and pass criteria. Every specific variant is registered
in [`research/VARIANT_LEDGER.md`](research/VARIANT_LEDGER.md) *before* its
backtest runs. Both files are append-only — nothing is ever edited or deleted,
including the failures and the mistakes. The ledger currently stands at **225
registered variants**.

**A strategy passes only if it beats buy-and-hold on BOTH total return and
maximum drawdown**, on dividend-adjusted data, over the same window. Ties fail.

**The test window is sealed.** Data from 2023 onward is sequestered on disk and
never loaded. Selection happens on 2010–2022 only. The loader raises on any
attempt to read a locked date, so contamination is a crash, not an oversight.

**Signals are causal by construction.** A strategy states its target weight at
day *t*'s close; the engine applies a one-day lag and fills at the next open.
Same-day execution is inexpressible through the interface. On top of that,
every run recomputes the strategy on randomly truncated data and fails if any
past decision changes — which caught three real look-ahead bugs.

**Costs are always on.** 2 bps per side on ETFs, real round-trip costs on
futures, financing on leverage, borrow on shorts. Anything trading more than
weekly is additionally reported at 2× and 3× those assumptions.

**Absurd results are treated as bugs.** Sharpe > 3, CAGR > 50%, hit rate > 90%,
or a suspiciously shallow drawdown withholds the verdict and demands a leakage
hunt before the number is shown.

## What the research found

Of ~110 published strategies tested across 225 variants, **almost everything
failed.** That is the honest result, and it is recorded rather than buried.

Sector cross-sectional momentum was the only mechanism to survive selection —
and then largely failed its own robustness checks: across 36 parameter settings
on two eras, the rank correlation of settings between eras was **−0.18**,
meaning which parameters look best is noise. Two apparent winners were
disqualified as engine artifacts after inspection.

## Live system

A paper-trading loop (Alpaca) runs the surviving book daily: pull bars, compute
signals from the close, submit market-on-open orders for the next session.

Two shutoff tiers, deliberately different:

| Tier | Trigger | Action |
|---|---|---|
| 1 | Rolling performance below a **matched random-entry** null, or drawdown past 1.2× the backtest worst | Block new entries; existing positions exit normally |
| 2 | Integrity failure — unknown symbol, stale data, exposure past hard caps, repeated API errors | **Flatten everything** and halt |

Performance decay is not an emergency; a system that no longer knows what it
owns is. Neither tier can clear itself — resuming requires a human edit.
Thresholds live in one owner-edited file whose hash is stamped into every log
line. Hard limits (position size, open positions, gross exposure) are separate,
in code, and cannot be relaxed by configuration.

**Real money is off.** `REAL_MONEY_ENABLED = False`, with four independent
paper-account checks re-verified before every order submission.

## Layout

```
research/
  IDEA_LOG.md          append-only idea registry
  VARIANT_LEDGER.md    append-only record of all 225 variants
  HALT_RULES.yaml      kill-switch thresholds (owner-edited only)
  engine/              backtester, cost model, look-ahead detection
  strategies/          ~110 published rules, indicators, calendars
  live/                Alpaca paper loop, kill switch, weekly reporting
  tests/               54 tests, mostly guarding the protocol itself
scripts/               data fetch, sweeps, era and neighborhood checks
```

Market data is not committed — [`scripts/fetch_data.py`](scripts/fetch_data.py)
reproduces it, and keeping it out also prevents the sealed test split from
being undone by a clone.
