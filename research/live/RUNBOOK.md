# Paper trading runbook

**Mode: PAPER ONLY.** `REAL_MONEY_ENABLED = False` in `live/config.py`. Four
independent checks (key prefix `PK`, `ALPACA_PAPER=true`, paper endpoint,
account number `PA…`) must all pass before any order, and they re-run before
every single submission — not just at startup.

Account in use: the paper account configured in `.env` (account number is printed at connect time; not recorded here).

## Schedule
Two **launchd** agents, weekdays (not cron — see below):

| Agent | When | Runs |
|---|---|---|
| `com.jainithin.tradingbot.daily` | 19:30 ET | `run_daily.sh` → `daily_loop.py`, plus `weekly_report.py` on Fridays |
| `com.jainithin.tradingbot.reconcile` | 09:40 ET | `run_daily.sh reconcile` → `reconcile_open.py` |

The checked-in source of truth for both plists is `live/launchd/`; the loaded
copies in `~/Library/LaunchAgents/` must match it. Inspect with
`launchctl list | grep tradingbot`; force a run with
`launchctl kickstart -w gui/$UID/com.jainithin.tradingbot.daily`; reload after
editing a plist with `launchctl bootout` then `bootstrap gui/$UID <plist>`.

**Why 19:30 ET, not just after the 16:00 close:** Alpaca only accepts OPG
(opening-auction) orders between **19:00 and 09:28 ET**. The daily loop was
first scheduled at 16:30; once the book was invested, every nightly rebalance
was refused with `code 40310000` and the live book silently stopped tracking
its targets (2026-08-25 through 08-27). The signal is computed from the day's
close regardless of run time, so the later slot costs nothing. `submit_qty`
now also turns that specific rejection into a journalled `rejected` with a
"daily run is mistimed" reason instead of a raw API error, so a future drift
is obvious in the journal.

**Why not cron:** cron silently SKIPS a job whose time passes while the Mac is
asleep. That is exactly what happened on 2026-08-24 — the 16:30 run never
fired and the book placed no orders at all that evening. launchd runs a missed
`StartCalendarInterval` job when the machine wakes instead. That catch-up is
also why `reconcile_open.py` refuses to act more than an hour after the open.

Output appends to `live/cron.log` (launchd's own stdout/stderr go to
`live/launchd.out` / `live/launchd.err`, and should stay empty). Exit codes:
0 ok · 2 tier-1 halt · 3 error · 4 tier-2 emergency.

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

## What the reconcile does each morning
OPG orders are **auction-only**: whatever the opening auction does not execute,
Alpaca marks `expired` a minute or two later — unfilled, not resting. On
2026-08-24 all four of the book's orders expired that way at 09:32–09:34 ET
and the account sat flat all day while the strategy believed it was invested.

`reconcile_open.py` runs at 09:40 ET and repairs that:
1. emergency halt active → do nothing at all
2. market must be OPEN **and** it must still be within 60 minutes of the open
   — a job that launchd deferred to 14:00 would be a different trade at a
   different price, so it stands down and lets the nightly loop re-decide
3. find orders that expired **today** (exchange time), subtract partial fills
   and any live resting order in the same direction
4. gate each remainder through the same hard limits and the same tier-1 entry
   halt as any other order
5. submit as a DAY market order, journalled with `replaces: <original id>`

It is idempotent — an order id that already appears as `replaces` in the
journal is never replaced twice, so running it repeatedly submits nothing
extra. The cost is a few minutes of slippage versus the opening print on the
days the auction fails.

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
