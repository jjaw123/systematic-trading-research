# Paper trading runbook

**Mode: PAPER ONLY.** `REAL_MONEY_ENABLED = False` in `live/config.py`. Four
independent checks (key prefix `PK`, `ALPACA_PAPER=true`, paper endpoint,
account number `PA…`) must all pass before any order, and they re-run before
every single submission — not just at startup.

Account in use: the paper account configured in `.env` (account number is printed at connect time; not recorded here).

## Schedule
Installed in cron, weekdays 16:30 ET:

    30 16 * * 1-5 research/live/run_daily.sh

That runs `daily_loop.py` and, on Fridays, `weekly_report.py`. Output appends
to `live/cron.log`. Exit codes: 0 ok · 2 tier-1 halt · 3 error · 4 tier-2
emergency.

## What the loop does each evening
1. connect + verify paper (×4)
2. pull adjusted daily bars into `live/market_cache/` (research code is
   blocked from reading this path, so the train/test split stays intact)
3. **tier-2 integrity scan** → if anything is wrong: flatten + halt, stop
4. **tier-1 performance check** → if halted: no new entries, exits still run
5. compute targets from the latest close (IDEA-109 risk layer @0.75%)
6. diff vs positions **plus pending orders**, gate through hard limits
7. submit market-on-open orders (whole shares, TIF=OPG) for the next session
8. journal a snapshot, append to `live_returns.csv`

## Hard limits (in code, `live/config.py` — not user-editable)
25% max single position · 6 max open positions · 100% max gross ·
25% max single order · 20 orders/day · $25 min notional.
These compose: each cap only tightens the size, the binding one wins.

## Two shutoff tiers, deliberately different
| | Trigger | Action |
|---|---|---|
| **Tier 1** | performance: worse than random entries, or drawdown past 1.2× backtest worst | block **new entries**; existing positions exit normally |
| **Tier 2** | integrity: unknown symbol held or ordered, stale data, exposure past hard caps, repeated API errors, broker account flags | **flatten everything** + halt |

Performance decay is not an emergency; system malfunction is. Neither tier
ever clears itself — both require a hand edit (`HALT_STATE.json` /
`EMERGENCY_HALT.json`) with the token from `HALT_RULES.yaml`.

## Files
- `JOURNAL.jsonl` — every decision, order, fill, rejection, event (append-only)
- `live_returns.csv` — equity/return/exposure series the halt checks consume
- `HALT_LOG.jsonl` — daily shutoff verdicts with the rules-file hash
- `reports/weekly_*.md` — weekly live-vs-backtest report
- `cron.log` — scheduler output

## Going to real money
Do not. Not until you say so explicitly. It requires editing
`REAL_MONEY_ENABLED` yourself, and the paper-endpoint and key-prefix checks
would also have to be revisited deliberately — they are not switches an agent
should flip.
