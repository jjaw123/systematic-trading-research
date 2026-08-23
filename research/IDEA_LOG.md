# IDEA LOG — Append-Only Registry of Trading Ideas

**Policy (fixed, applies to this file forever):**
1. Every idea must be logged here BEFORE any code is written or any test is run on it.
2. Entries are NEVER edited or deleted. Corrections, refinements, and new variants get NEW entries that reference the original by ID.
3. Every entry must contain: timestamp, exact rule, allowed settings, and pass criteria.
4. Testing an idea also requires registering each specific variant in `VARIANT_LEDGER.md` before the test runs.

**Global pass criteria (referenced by every entry as "PASS-STD"):**
A variant passes only if, over the identical test period and on dividend-adjusted data, it beats buy-and-hold of the traded asset (or, for multi-asset strategies, buy-and-hold of the equal-weight basket of the universe) on BOTH:
- Total return (higher), AND
- Maximum drawdown (smaller in magnitude).
Both conditions required. Ties fail.

**Source of first 44 entries:** `/Users/Jainithin/Downloads/50_trading_strategies.md` (user's shortlist, 2026-08-23). Original doc numbering preserved as "Doc #". The 6 candidates that failed the doc's own grading (#13, #25, #30, #32, #35, #39) are intentionally not logged.

---

## IDEA-001 — Golden Cross (50/200 SMA) [Doc #1]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long when SMA(50) > SMA(200) of daily close; flat otherwise. Crossover checked on close, rebalance daily. Optional variant per source: short instead of flat when SMA(50) < SMA(200).
- Allowed settings: SMA periods fixed at 50/200. Instruments: SPY, QQQ, GLD, large trending stocks. Long/flat or long/short.
- Pass criteria: PASS-STD.

## IDEA-002 — 200-Day SMA Trend Filter [Doc #2]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long when close > SMA(200); else 100% cash (or short-term bonds, e.g., AGG/BIL). Check daily or monthly.
- Allowed settings: SMA period fixed at 200. Check frequency: daily or monthly. Instruments: SPY, EFA, GLD, VNQ. Cash proxy: cash or short-term bonds.
- Pass criteria: PASS-STD.

## IDEA-003 — Time-Series Momentum, 12-Month [Doc #3]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: On the last trading day of each month, go long if trailing 252-day total return > 0, else flat; hold 1 month.
- Allowed settings: Lookback fixed at 12 months (252 trading days). Monthly rebalance. Instruments: GLD, SPY, broad liquid/sector ETFs. Long/flat (long/short allowed per source).
- Pass criteria: PASS-STD.

## IDEA-004 — Cross-Sectional Momentum (Relative Strength) [Doc #4]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Monthly, rank universe (S&P 500 constituents or sector-ETF universe) by return over months t−12 to t−1, skipping the most recent month. Long top decile, equal-weighted; hold 1 month; rebalance monthly.
- Allowed settings: Formation window 6–12 months (skip-month always applied). Holding period 1–3 months. Universe: S&P 500 constituents or sector ETFs. Not applicable to solo gold.
- Pass criteria: PASS-STD (benchmark = equal-weight buy-and-hold of the universe).

## IDEA-005 — Dual Momentum [Doc #5]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Universe = {SPY, EFA, AGG}. Monthly, hold whichever of SPY/EFA has the higher trailing 12-month return, but only if that asset's own 12-month return > 0; otherwise hold AGG.
- Allowed settings: Lookback fixed at 12 months, monthly rebalance. Universe may extend to include GLD per source ("SPY/EFA/AGG/GLD rotation").
- Pass criteria: PASS-STD (benchmark = equal-weight buy-and-hold of the universe).

## IDEA-006 — MACD Trend (12,26,9) [Doc #6]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: MACD(12,26) vs signal(9) on daily close. Long when MACD line > signal line; flat (or short) on cross below.
- Allowed settings: Parameters fixed at 12/26/9. Instruments: SPY, index ETFs, GLD, large caps. Long/flat or long/short.
- Pass criteria: PASS-STD.

## IDEA-007 — Parabolic SAR [Doc #7]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Wilder standard parameters: AF start 0.02, step 0.02, max 0.20. Long while price > SAR; flip short when price < SAR.
- Allowed settings: AF parameters fixed (0.02/0.02/0.20). Instruments: GLD, trending index ETFs. Long/short as published (long/flat variant permitted).
- Pass criteria: PASS-STD.

## IDEA-008 — Triple Moving Average Alignment [Doc #8]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: EMA(4), EMA(9), EMA(18) on close. Long only when EMA4 > EMA9 > EMA18; flat otherwise.
- Allowed settings: EMA periods fixed at 4/9/18. Instruments: trending ETFs, GLD, momentum stocks.
- Pass criteria: PASS-STD.

## IDEA-009 — 52-Week High Momentum [Doc #9]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy stocks/ETFs trading within 5% of their 252-day high; hold 6 months; rebalance monthly.
- Allowed settings: Proximity threshold: within 5% (source Part 1 allows "within X%"; default 5%). Holding period 1–6 months. Universe: individual stocks, sector ETFs. Not gold.
- Pass criteria: PASS-STD (benchmark = equal-weight buy-and-hold of the universe).

## IDEA-010 — ADX/DMI Directional Movement System [Doc #10]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: ADX(14), +DI(14), −DI(14). Long when +DI crosses above −DI while ADX > 25; exit on the opposite DI cross.
- Allowed settings: Period fixed at 14. ADX threshold 20–25 (default 25). Instruments: GLD, trending ETFs, momentum stocks.
- Pass criteria: PASS-STD.

## IDEA-011 — RSI(2) Mean Reversion (Connors) [Doc #11]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy when close > SMA(200) AND RSI(2) < 10; sell when RSI(2) > 70 OR close > SMA(5).
- Allowed settings: RSI period fixed at 2; entry threshold 10; exit thresholds 70 / SMA(5); trend filter SMA(200). All fixed per Connors. Universe: SPY, QQQ, liquid large caps.
- Pass criteria: PASS-STD.

## IDEA-012 — Bollinger Band Reversion [Doc #12]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Bollinger Bands (20-day, 2σ). Buy when close < lower band; sell when price reaches SMA(20) (middle band).
- Allowed settings: Parameters fixed at 20/2σ. Universe: SPY, range-bound large caps.
- Pass criteria: PASS-STD.

## IDEA-013 — Short-Term 1-Week Reversal [Doc #14]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Weekly, within the S&P 500 universe, long the bottom decile by trailing 5-trading-day return (long-only variant), or long bottom decile / short top decile; hold 5 trading days.
- Allowed settings: Ranking window fixed at 5 trading days; holding period 5 trading days; decile buckets. Universe: liquid large/mid caps (S&P 500). Long-only or long/short.
- Pass criteria: PASS-STD (benchmark = equal-weight buy-and-hold of the universe).

## IDEA-014 — Internal Bar Strength (IBS) Reversion [Doc #15]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: IBS = (Close − Low) / (High − Low). Buy when IBS < 0.2; exit at next close, or when IBS > 0.8.
- Allowed settings: Thresholds fixed at 0.2 / 0.8. Exit: next close or IBS > 0.8. Instruments: SPY, GLD.
- Pass criteria: PASS-STD.

## IDEA-015 — Williams %R Oversold Bounce [Doc #16]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: %R(14). Buy when %R < −90; exit when %R > −50.
- Allowed settings: Period fixed at 14; thresholds fixed at −90 / −50. Universe: SPY, liquid large caps.
- Pass criteria: PASS-STD.

## IDEA-016 — Moving Average Envelope Reversion [Doc #17]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: 20-day SMA ± 5% envelope. Sell/short when price > upper (+5%) envelope; cover/exit at SMA(20).
- Allowed settings: SMA period fixed at 20; envelope width N% with default 5%. Universe: SPY, large caps in choppy regimes.
- Pass criteria: PASS-STD.

## IDEA-017 — Overnight Gap Fade [Doc #18]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: If today's open is ≥2% below the prior close with no earnings/news catalyst that day, buy at open, sell at same-day close.
- Allowed settings: Gap threshold: ≥2% (source Part 1 allows ">X%"; default 2%). Universe: SPY, liquid large caps. No-news filter required for single names.
- Pass criteria: PASS-STD.

## IDEA-018 — Stochastic Oscillator Reversion [Doc #19]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: %K(14), %D(3). Buy when %K crosses above %D while below 20; sell when %K crosses below %D while above 80.
- Allowed settings: Parameters fixed at 14/3; bands fixed at 20/80. Universe: SPY, range-bound large caps.
- Pass criteria: PASS-STD.

## IDEA-019 — Pairs / Spread Reversion [Doc #20]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: For pair GLD/SLV (or XLE/XLB): compute 60-day rolling z-score of the price ratio. When z = +2, short outperformer / long underperformer; mirror at z = −2; exit both legs at z = 0.
- Allowed settings: Z-score window fixed at 60 days; entry ±2, exit 0. Pairs: GLD/SLV, XLE/XLB, or other correlated ETF/sector pairs.
- Pass criteria: PASS-STD (benchmark = equal-weight buy-and-hold of the two legs).

## IDEA-020 — Donchian 20/10 Breakout (Turtle System 1) [Doc #21]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy on close > highest high of prior 20 days; exit on close < lowest low of prior 10 days.
- Allowed settings: Channels fixed at 20-in / 10-out. Instruments: GLD, trending ETFs.
- Pass criteria: PASS-STD.

## IDEA-021 — Donchian 55/20 Breakout (Turtle System 2) [Doc #22]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy on close > highest high of prior 55 days; exit on close < lowest low of prior 20 days.
- Allowed settings: Channels fixed at 55-in / 20-out. Instruments: GLD, broad trending ETFs.
- Pass criteria: PASS-STD.

## IDEA-022 — 52-Week High Breakout [Doc #23]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy on a new 252-day closing high; exit when close < SMA(50).
- Allowed settings: Lookback fixed at 252 days; exit SMA fixed at 50. Universe: growth stocks, sector ETFs.
- Pass criteria: PASS-STD.

## IDEA-023 — ATR Volatility Breakout [Doc #24]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy when close > prior close + 1.5 × ATR(14); mirror for shorts (close < prior close − 1.5 × ATR(14)); exit on opposite-direction signal.
- Allowed settings: ATR period fixed at 14; multiplier k in 1–2 (default 1.5). Instruments: GLD, trending ETFs. Long-only variant permitted.
- Pass criteria: PASS-STD.

## IDEA-024 — Bollinger Squeeze Breakout [Doc #26]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: BB(20, 2σ). Squeeze = bandwidth at a 6-month low. After a squeeze, buy on close above the upper band; exit on close below SMA(20).
- Allowed settings: BB parameters fixed at 20/2σ; squeeze lookback 6 months. Instruments: GLD, trending ETFs.
- Pass criteria: PASS-STD.

## IDEA-025 — Consolidation/Resistance Breakout [Doc #27]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Identify a horizontal resistance level touched ≥8 times over 3–6 months (swing highs within 1% of each other); buy on a decisive close >1% above that level.
- Allowed settings: Touch count ≥8; window 3–6 months; touch tolerance 1%; breakout margin 1%. Instruments: individual stocks, GLD.
- Pass criteria: PASS-STD.

## IDEA-026 — Volume-Confirmed Breakout [Doc #28]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy on close > 20-day high AND day's volume > 1.5 × SMA(volume, 50).
- Allowed settings: Price channel fixed at 20 days; volume multiplier 1.5×; volume SMA 50. Universe: liquid large-cap stocks, ETFs (not gold).
- Pass criteria: PASS-STD.

## IDEA-027 — Post-Earnings Gap Continuation (PEAD) [Doc #29]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Buy stocks that gap up ≥3% on earnings day and close in the top third of that day's range; hold 20 trading days.
- Allowed settings: Gap threshold 3%; close-position filter: top third of day range; holding period fixed at 20 trading days. Universe: individual stocks with earnings dates (requires earnings-date data).
- Pass criteria: PASS-STD.

## IDEA-028 — Sell in May / Halloween Indicator [Doc #31]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long SPY Nov 1 – Apr 30; flat/cash May 1 – Oct 31.
- Allowed settings: Dates fixed. Instruments: SPY, broad equity ETFs. Not GLD.
- Pass criteria: PASS-STD.

## IDEA-029 — Turn-of-the-Month Effect [Doc #33]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long from the last trading day of each month through the 3rd trading day of the next month; flat otherwise.
- Allowed settings: Window: last trading day through trading day 3–4 of new month (default day 3). Instruments: SPY, QQQ.
- Pass criteria: PASS-STD.

## IDEA-030 — Santa Claus Rally [Doc #34]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long SPY from the 5th-to-last trading day of December through the 2nd trading day of January; flat the rest of the year.
- Allowed settings: Dates fixed. Instruments: SPY, broad equity ETFs.
- Pass criteria: PASS-STD.

## IDEA-031 — Gold Seasonal Strength (Sept–Feb) [Doc #36]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long GLD September 1 through end of February; flat March 1 – August 31.
- Allowed settings: Dates fixed. Instrument: GLD (or gold futures) only.
- Pass criteria: PASS-STD.

## IDEA-032 — Pre-Holiday Effect [Doc #37]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long SPY for the single trading day immediately before each of: New Year's Day, Presidents' Day, Good Friday, Memorial Day, July 4th, Labor Day, Thanksgiving, Christmas; flat otherwise.
- Allowed settings: Holiday list fixed as above. Instruments: SPY, broad equity ETFs.
- Pass criteria: PASS-STD.

## IDEA-033 — End-of-Quarter Window Dressing [Doc #38]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Long the top-return-decile S&P 500 stocks (trailing quarter return) for the final 5 trading days of each calendar quarter; flat otherwise.
- Allowed settings: Ranking window: trailing quarter; holding window: final 5 trading days of quarter; decile buckets. Universe: S&P 500 stocks, sector ETFs.
- Pass criteria: PASS-STD (benchmark = equal-weight buy-and-hold of the universe).

## IDEA-034 — Asset-Specific Month-of-Year Seasonality [Doc #40]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: For GLD/SPY, compute each calendar month's historical average return over 20+ years of data (in-sample window only, walk-forward — no look-ahead); hold the asset only during its top 4–6 historically strongest months.
- Allowed settings: History requirement ≥20 years; months held: top 4–6. Instruments: GLD, broad equity ETFs with long histories. Not short-history single names.
- Pass criteria: PASS-STD.

## IDEA-035 — Fixed-Fractional Risk Sizing, 1% Rule [Doc #41] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay on any entry/exit strategy above: risk 1% of current equity per trade; shares = (equity × 0.01) / (entry − stop).
- Allowed settings: Risk per trade 1–2% (default 1%). Applies to any asset.
- Pass criteria: PASS-STD for the combined base-strategy + overlay variant; each combo is its own ledger variant.

## IDEA-036 — Volatility-Based "N" (ATR) Sizing [Doc #42] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: N = ATR(20); units = (equity × 0.01) / (N × dollar value per point).
- Allowed settings: ATR period fixed at 20; risk fraction 1%. Applies to any asset.
- Pass criteria: PASS-STD for the combined variant.

## IDEA-037 — Fractional Kelly Sizing [Doc #43] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: from the base strategy's own last 30+ closed trades compute W (win rate) and R (avg win / avg loss); f* = W − (1−W)/R; size at 0.5×f* or 0.25×f*.
- Allowed settings: Fraction: 0.25× or 0.5× Kelly; minimum 30 trades of history before activation. Not valid for systems with too few trades.
- Pass criteria: PASS-STD for the combined variant.

## IDEA-038 — Volatility Targeting, Constant-Vol [Doc #44] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: target 10% annualized vol. Weekly, exposure multiplier = target vol / trailing 20-day realized vol (annualized), capped to [0.25×, 2×].
- Allowed settings: Target vol 10%; realized-vol window 20 days; weekly adjustment; leverage cap [0.25, 2].
- Pass criteria: PASS-STD for the combined variant (or applied to a buy-and-hold portfolio as its own variant).

## IDEA-039 — Equal-Weight 1/N Rebalancing [Doc #45]
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Equal-weight {SPY, GLD, and 3–5 sector ETFs}; rebalance to equal weights on the 1st trading day of each month.
- Allowed settings: Basket: SPY + GLD + 3–5 sector ETFs; rebalance frequency monthly or quarterly.
- Pass criteria: PASS-STD (benchmark = same basket bought equal-weight at start and never rebalanced).

## IDEA-040 — Pyramiding (Unit-Adding on Winners) [Doc #46] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay on trend entries (e.g., IDEA-020/023): add 1 fixed-risk unit every 0.5×ATR(20) of favorable move, max 4 units, each unit independently stopped at 2×ATR(20).
- Allowed settings: Add spacing 0.5×ATR(20); max 4 units; per-unit stop 2×ATR(20). Trend/breakout bases only.
- Pass criteria: PASS-STD for the combined variant.

## IDEA-041 — ATR-Based 2N Stop [Doc #47] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: stop = entry − 2×ATR(20) for longs (entry + 2×ATR(20) for shorts); size so a stop-out loses exactly the per-trade risk % (per IDEA-035).
- Allowed settings: Stop multiple fixed at 2×ATR(20). Applies to any asset.
- Pass criteria: PASS-STD for the combined variant.

## IDEA-042 — Max Position / Correlation Cap [Doc #48] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: no single position > 25% of equity; combined exposure of positions with pairwise correlation > 0.7 capped at 60% of equity.
- Allowed settings: Single-position cap 20–25% (default 25%); correlation threshold 0.7; correlated-group cap 60%.
- Pass criteria: PASS-STD for the combined variant.

## IDEA-043 — Anti-Martingale Discipline [Doc #49] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: after any losing trade, never raise the next trade's base risk % above the strategy default (1%); scale up only after wins via pyramiding (IDEA-040); reduce after loss streaks.
- Allowed settings: Base risk 1%; scaling only per pyramiding rule.
- Pass criteria: PASS-STD for the combined variant.

## IDEA-044 — Portfolio Heat Cap [Doc #50] (overlay)
- Logged: 2026-08-23 16:16 EDT
- Exact rule: Overlay: sum of (position size × distance to stop) across all open positions ≤ 6% of equity; skip new entry signals while at the cap.
- Allowed settings: Heat cap fixed at 6% of equity.
- Pass criteria: PASS-STD for the combined variant.

---
*(Append new entries below this line. Never modify anything above it.)*

**Batch 2 — source: `/Users/Jainithin/Downloads/150_trading_strategies.md` (user's updated 150-candidate list, 2026-08-23). Only entries graded PASS in that file with a concrete test rule, that are NOT duplicates of IDEA-001..044 (the file's own duplicate flags respected — flagged clusters collapse to one entry). Original doc numbering as "150 #N". All entries logged 2026-08-23 16:58 EDT. Pass criteria for every entry: PASS-STD (see header).**

## IDEA-045 — Dual SMA Crossover 10/30 [150 #3]
- Exact rule: Long when SMA(10) > SMA(30) of daily close; flat otherwise. Assets: GLD, SPY.
- Allowed settings: periods fixed 10/30.

## IDEA-046 — Triple SMA Alignment 5/20/50 [150 #4]
- Exact rule: Long SPY when SMA(5) > SMA(20) > SMA(50); flat otherwise.
- Allowed settings: periods fixed 5/20/50.

## IDEA-047 — Absolute Momentum vs T-bill Hurdle [150 #10]
- Exact rule: Monthly: hold SPY if its trailing 12-month return > trailing 12-month T-bill (SHY) return, else hold SHY.
- Allowed settings: lookback fixed 12m; hurdle = SHY (or 90-day T-bill).

## IDEA-048 — Dual Momentum, 4-Asset with Cash Hurdle [150 #11]
- Exact rule: Monthly, among {SPY, EFA, GLD, IEF}: hold the asset with highest trailing 12-month return, only if that return also exceeds SHY's; else hold SHY.
- Allowed settings: universe and lookback fixed as stated.

## IDEA-049 — Ivy 5 Tactical Allocation [150 #12]
- Exact rule: 20% each SPY/VEU/AGG/VNQ/GLD; each month-end hold a sleeve only if its price > 200-day SMA, else that sleeve in cash.
- Allowed settings: universe fixed; 200-day SMA; monthly check.

## IDEA-050 — ADX-Gated Golden Cross [150 #14]
- Exact rule: Golden Cross (IDEA-001) on SPY only when ADX(14) ≥ 25; otherwise cash regardless of MA state.
- Allowed settings: ADX threshold 25 (stand-aside below 20-25).

## IDEA-051 — Keltner Channel Breakout [150 #16]
- Exact rule: Long GLD when Close > EMA(20) + 2×ATR(10); exit when Close < EMA(20).
- Allowed settings: fixed as stated.

## IDEA-052 — Aroon Trend System [150 #17]
- Exact rule: Long GLD when Aroon-Up(25) > 70 AND Aroon-Down(25) < 30; exit when Aroon-Up < 50.
- Allowed settings: fixed as stated.

## IDEA-053 — Rate-of-Change 125-Day Filter [150 #18]
- Exact rule: Long SPY when 125-day ROC > 0; flat otherwise; daily check.
- Allowed settings: fixed.

## IDEA-054 — 10-Month SMA Timing (Faber monthly) [150 #19]
- Exact rule: At each month-end, hold the asset if price > 10-month SMA (of month-end closes), else cash until next month-end. Assets: SPY, GLD.
- Allowed settings: fixed.

## IDEA-055 — Weekly Golden Cross 10/40-Week [150 #20]
- Exact rule: Long SPY when SMA(10) of weekly closes > SMA(40) of weekly closes (completed weeks only); flat otherwise; checked daily.
- Allowed settings: fixed.

## IDEA-056 — EMA Crossover 12/26 [150 #21]
- Exact rule: Long GLD when EMA(12) > EMA(26); flat otherwise.
- Allowed settings: fixed.

## IDEA-057 — Elder Triple Screen (simplified per source) [150 #22]
- Exact rule: On SPY, only long when weekly MACD(12,26,9) line > signal (completed weeks); enter at next open when daily RSI(2) < 10; exit when RSI(2) > 70.
- Allowed settings: fixed.

## IDEA-058 — Chandelier Exit on Donchian Entry [150 #23]
- Exact rule: GLD: enter on Donchian 20-day-high close (IDEA-020 entry); exit when Close < (highest close since entry − 3×ATR(22)).
- Allowed settings: fixed.

## IDEA-059 — SuperTrend 10/3 [150 #24]
- Exact rule: GLD: ATR(10), multiplier 3.0; long while price above SuperTrend line, flat on flip (short allowed per source).
- Allowed settings: fixed.

## IDEA-060 — Linear Regression Slope 50-Day [150 #25]
- Exact rule: Long SPY when the 50-day linear-regression slope of close is positive; flat otherwise.
- Allowed settings: fixed.

## IDEA-061 — Donchian 4-Week Rule, symmetric long/short [150 #26]
- Exact rule: GLD: long on close > prior 20-day high; flip flat/short on close < prior 20-day low.
- Allowed settings: long/short as published; long/flat variant permitted.

## IDEA-062 — ATR Trailing Stop on Golden Cross [150 #27]
- Exact rule: SPY: enter on Golden Cross; exit when Close < (highest close since entry − 2×ATR(14)); re-enter on fresh cross.
- Allowed settings: fixed.

## IDEA-063 — Moving Average Ribbon 10/20/30/40/50 [150 #28]
- Exact rule: Long GLD when SMA(10)>SMA(20)>SMA(30)>SMA(40)>SMA(50); flat when the order breaks.
- Allowed settings: fixed.

## IDEA-064 — Riding the Upper Bollinger Band [150 #29]
- Exact rule: GLD: enter/hold while daily close ≥ upper Bollinger Band (20,2σ); exit when close falls back inside the bands.
- Allowed settings: fixed.

## IDEA-065 — 52-Week High Momentum with Trailing Exit [150 #30]
- Exact rule: Buy when within 5% of 252-day high AND trailing 3-month return > 0; exit when price falls 10% below the 252-day high. Assets: broad ETFs / stocks (SPY; AAPL).
- Allowed settings: fixed. Not gold.

## IDEA-066 — Relative Strength Sector Rotation, Top 3 [150 #31]
- Exact rule: Month-end, rank the 9 SPDR sector ETFs (XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY) by 6-month total return; hold top 3 equal-weight next month.
- Allowed settings: ranking window 6-12m; top 2-3; monthly.

## IDEA-067 — Volatility-Adjusted Trend Filter [150 #35]
- Exact rule: SPY: monthly, long when (trailing 12-month return / trailing 12-month annualized daily vol) > 0.3; else cash.
- Allowed settings: fixed.

## IDEA-068 — Double 7's (Connors) [150 #38]
- Exact rule: SPY: buy when close is a new 7-day low AND Close > SMA(200); sell when close makes a new 7-day high.
- Allowed settings: fixed.

## IDEA-069 — TPS PercentRank (Connors) [150 #39]
- Exact rule: SPY: buy when 3-day average of PercentRank(Close, 100) < 15 AND Close > SMA(200); sell when > 70.
- Allowed settings: fixed.

## IDEA-070 — Williams %R with Trend Gate [150 #43]
- Exact rule: SPY: buy when %R(14) < −90 AND Close > SMA(200); sell when %R(14) > −20.
- Allowed settings: fixed (distinct from IDEA-015's ungated −90/−50 version).

## IDEA-071 — Stochastic with Trend Gate [150 #44]
- Exact rule: SPY: buy when %K(14,3) crosses above 20 from below AND Close > SMA(200); sell when %K crosses below 80.
- Allowed settings: fixed.

## IDEA-072 — RSI(3)/RSI(4) Connors Variants [150 #45]
- Exact rule: As IDEA-011 but RSI period 3 or 4 (entry <10, exit >70 or close > SMA(5), 200-day gate). SPY.
- Allowed settings: RSI period ∈ {3,4}.

## IDEA-073 — Percent-Below-MA Reversion with Trend Gate [150 #53]
- Exact rule: SPY: buy when Close ≥5% below SMA(20) AND Close > SMA(200); sell when Close ≥ SMA(20). (Supersedes the ungraded folklore #13 from the 50-list: the 150-list grades this PASS with published lineage.)
- Allowed settings: envelope 3-5% (default 5).

## IDEA-074 — ADX-Low Gate on RSI(2) [150 #54]
- Exact rule: Apply IDEA-011 (RSI-2) on SPY only when ADX(14) < 20; no entries when ADX ≥ 25.
- Allowed settings: fixed.

## IDEA-075 — Consecutive Down-Days Reversal [150 #56]
- Exact rule: SPY: buy after 3 consecutive lower closes AND Close > SMA(200); sell after 2 consecutive higher closes.
- Allowed settings: fixed.

## IDEA-076 — 52-Week Low Bounce (failed breakdown) [150 #57]
- Exact rule: Individual stocks (AAPL, MSFT): if a new 252-day intraday low is made but the close is back above that prior low, buy next open; hold 5 trading days or exit on a fresh new low.
- Allowed settings: fixed.

## IDEA-077 — Keltner Fade with ADX Gate [150 #60]
- Exact rule: SPY: buy when Close < EMA(20) − 2×ATR(10) AND ADX(14) < 20; sell at EMA(20).
- Allowed settings: fixed.

## IDEA-078 — Donchian Fade with ADX Gate [150 #61]
- Exact rule: SPY: when ADX(14) < 20, short at 20-day-high touch and long at 20-day-low touch; exit at channel midline.
- Allowed settings: fixed.

## IDEA-079 — VIX Spike Mean Reversion [150 #51]
- Exact rule: Buy SPY when VIX closes > 1.2 × its 10-day SMA; sell when VIX closes back below its 10-day SMA. (VIX is signal data only, never a position.)
- Allowed settings: fixed.

## IDEA-080 — Williams Volatility Breakout (daily adaptation) [150 #75]
- Exact rule: GLD: buy at next open when today's (High−Low) > 1.5 × 10-day ATR AND close in top third of the day's range; exit next day.
- Allowed settings: fixed.

## IDEA-081 — ATR Channel Breakout with Chandelier Exit [150 #76]
- Exact rule: GLD: buy when Close > (prior Close + 2×ATR(20)); exit when Close < (highest close since entry − 2×ATR(20)).
- Allowed settings: fixed (distinct from IDEA-023: k=2, ATR(20), trailing exit).

## IDEA-082 — Range-Compression (Triangle) Breakout [150 #79]
- Exact rule: GLD: when 20-day high-low range < 50% of its value 20 days prior, buy on close above the recent 20-day range high; exit per 10-day low.
- Allowed settings: fixed.

## IDEA-083 — Flag/Pennant Breakout, parameterized [150 #82]
- Exact rule: GLD: after a ≥8% move in 10 trading days, buy on close above the high of the subsequent 3-10-day tight range (daily range < 50% of impulse's avg daily range); stop at the flag low. (The 50-list's #30 failed for vagueness; the 150-list supplies objective parameters.)
- Allowed settings: fixed as stated.

## IDEA-084 — OBV-Confirmed Breakout [150 #86]
- Exact rule: Stocks (AAPL, MSFT): buy on a 20-day closing high coinciding with OBV also at a 20-day high; stop at prior 10-day low.
- Allowed settings: fixed.

## IDEA-085 — Swing-High Breakout (3% swing definition) [150 #89]
- Exact rule: GLD: swing high = local peak followed by ≥3% decline; buy on close above the most recent swing high; stop below the pullback low.
- Allowed settings: fixed.

## IDEA-086 — Gold Multi-Month Base Breakout [150 #90]
- Exact rule: GLD: buy on close above prior 126-day high, provided the prior 126-day range < 15% of price; trailing exit at the 60-day low.
- Allowed settings: fixed.

## IDEA-087 — Prior-Year-High Breakout [150 #92]
- Exact rule: SPY: buy on first close above the prior calendar year's highest close; exit on close below the prior calendar year's lowest close.
- Allowed settings: fixed.

## IDEA-088 — NR7 Breakout (daily-causal adaptation) [150 #93]
- Exact rule: GLD: flag NR7 when today's High−Low is the smallest of the last 7 days. Adaptation for next-open execution: enter at next open after a close above the NR7 day's high; exit on close below the NR7 day's low. (Published version uses an intraday stop order; adaptation noted.)
- Allowed settings: fixed.

## IDEA-089 — Ross Hook Pullback Breakout [150 #95]
- Exact rule: GLD, only when Close > SMA(200): buy on close above the high of the bar preceding the most recent 2-3-day pullback low; stop below that pullback low.
- Allowed settings: fixed.

## IDEA-090 — Gold Seasonal Aug 25 – Oct 31 [150 #104]
- Exact rule: Long GLD from Aug 25 through Oct 31 each year; flat otherwise. (Distinct window from IDEA-031's Sept-Feb.)
- Allowed settings: fixed.

## IDEA-091 — Triple-Witching Week Drift (adapted) [150 #105]
- Exact rule: SPY: published = buy Thursday close before quarterly triple-witching Friday (3rd Fri of Mar/Jun/Sep/Dec), sell following Monday close. Protocol adaptation: hold from Friday open through the following Tuesday open.
- Allowed settings: fixed; adaptation noted.

## IDEA-092 — Pre-FOMC Announcement Drift (adapted) [150 #111]
- Exact rule: SPY: published = buy at close 24h before each scheduled FOMC statement, sell at announcement-day close. Protocol adaptation: hold announcement-day open to next open. REQUIRES: historical FOMC meeting calendar (exogenous, published in advance) — not yet in the project.
- Allowed settings: fixed; blocked until FOMC calendar data added.

## IDEA-093 — Risk Parity SPY/GLD/IEF [150 #127]
- Exact rule: Weight SPY, GLD, IEF each inversely to trailing 60-day realized vol, normalized to 100%; rebalance monthly.
- Allowed settings: fixed.

## IDEA-094 — CPPI (floor 90%, multiplier 3) [150 #129]
- Exact rule: SPY risky asset: risky allocation = min(100%, 3 × (V − 0.9×V0)/V), remainder cash; rebalance weekly.
- Allowed settings: fixed.

## IDEA-095 — Drawdown-Based De-Risking Overlay [150 #137]
- Exact rule: On Donchian 20/10 GLD (IDEA-020): halve position size after a 10% strategy-equity drawdown; restore full size only at a new strategy-equity high.
- Allowed settings: fixed.

## IDEA-096 — VIX-Scaled SPY Exposure [150 #142]
- Exact rule: SPY weight = 20 / VIX, capped [0.25, 1.0]; rebalance weekly. (VIX = signal data only.)
- Allowed settings: fixed.

## IDEA-097 — Barbell 90/10 [150 #148]
- Exact rule: 90% in T-bills (BIL); 10% sleeve deployed in Donchian 20/10 GLD (IDEA-020) when long, else also in cash.
- Allowed settings: fixed.

## IDEA-098 — Rebalancing Bands 5/25 on 60/40 SPY/GLD [150 #149]
- Exact rule: Target 60% SPY / 40% GLD; rebalance to target only when SPY weight exits [55%, 65%].
- Allowed settings: fixed.

## IDEA-099 — Overnight Reversal After Down Day [150 #47]
- Exact rule: SPY: after a down day, buy at that day's close, sell at next day's open. PROTOCOL-BLOCKED: requires close execution, which the engine's decide-at-close/execute-next-open rule cannot express. Logged for the record; untestable under current protocol.

## IDEA-100 — Darvas Box Breakout [150 #74]
- Exact rule: Stocks: box = tightest 3-week range "after a run-up"; buy close above box high with volume > 1.5×50-day average; stop at box low. BLOCKED: "run-up" is not objectively defined in the source; defining it ourselves would add unpublished parameters.

## IDEA-101 — Round-Number Breakout [150 #81]
- Exact rule: Stocks: after price capped below a round number for 3+ months, buy first close above it with volume > 1.3×50-day average; stop below the level. Note: round-number granularity unspecified in source; deferred pending a spec.

## IDEA-102 — Inverse-Volatility Weights in Rotation Basket [150 #136]
- Exact rule: For IDEA-066's top-3 sector basket: weight each holding by 1/(20-day vol), normalized, instead of equal weight.
- Allowed settings: fixed.

**Batch 3 — source: user-supplied strategy cards (screenshots, 2026-08-23 17:23 EDT). The cards display out-of-sample performance claims from an external run, including TEST-period figures; those claims are NOT evidence under this protocol and are deliberately not recorded here — only the rules are. All entries logged 2026-08-23 17:26 EDT. Pass criteria: PASS-STD.**

## IDEA-103 — Trend Core: QQQ above 200dMA, else GLD [card A]
- Exact rule: Hold QQQ while QQQ close > its 200-day SMA; hold GLD while below. Signal at close, trade next open.
- Allowed settings: fixed. Benchmark: EW QQQ/GLD basket (PASS-STD).

## IDEA-104 — 52wk-High ETF Rotation with SPY Trend Gate [card B]
- Exact rule: Monthly, hold the 5 ETFs closest to their 52-week highs (ratio close / 252d max close); go 100% cash when SPY < its 200-day SMA.
- Allowed settings: top 5; monthly. Published universe "50 ETFs"; ADAPTATION: our available 19-ETF universe (SPY QQQ IWM EFA VEU AGG IEF SHY VNQ GLD SLV + 9 SPDR sectors) until a broader list is supplied.

## IDEA-105 — IBS Dip-Sniper 0.1/0.9 with 3-Day Time Stop [card C]
- Exact rule: SPY: buy when the close lands in the bottom 10% of the day's range (IBS <= 0.1) AND close > SMA(200); exit when IBS >= 0.9 or after 3 days.
- Allowed settings: thresholds 0.1/0.9; max hold 3 days. Note: card states these params were tuned on the (external) train set.

## IDEA-106 — NQ Opening-Range Breakout 30-min [card D]
- Exact rule: Trade the break of the first 30 minutes' range on NQ futures; stop at far side; flat by close.
- BLOCKED: requires intraday NQ futures data (none in project) and intraday execution outside the decide-at-close/execute-next-open protocol. Logged for the record only.

## IDEA-107 — Vol-Targeting Overlay 20%, cap 2x, on QQQ [card E]
- Exact rule: QQQ exposure = 20% target vol / trailing 20-day realized vol (annualized), capped at 2.0x. Sizing layer, not a signal.
- Allowed settings: fixed. Financing on leverage per engine cost rules. Benchmark: QQQ B&H.

## IDEA-108 — Survivor Blend, Inverse-Vol Weighted
- Exact rule: Combine the daily net return streams of all currently-surviving strategies; weights proportional to 1 / trailing 63-day vol of each stream, normalized; recompute at month-end, apply next day; no other tuning.
- Allowed settings: fixed as stated. Report vs SPY and QQQ buy-and-hold. Note: inter-strategy reallocation costs not modeled (monthly, small); each stream is already net of its own costs.

**Batch 4 — logged 2026-08-23 17:32 EDT. Pass criteria: PASS-STD.**

## IDEA-109 — Portfolio Risk Layer (unlevered, 20% book vol target)
- Exact rule: Applied to the surviving book (IDEA-066 sector rotation + IDEA-107 vol-targeted QQQ). For each instrument with a live signal: position weight = risk_pct / (exit_distance / price), where exit_distance = 2 x ATR(20) (Turtle 2N convention per IDEA-041). Then: (a) cap any single position at 25% of equity; (b) cap total open positions at 6 concurrent and gross exposure at 100%; (c) scale the whole book by min(20% / trailing-20d annualized realized vol of the unscaled book, 1.0) so the book targets 20% annualized vol without leverage.
- Allowed settings: risk_pct in [0.5%, 1.0%] per the brief (tested at 0.5 / 0.75 / 1.0); single-position cap 25%; max 6 open positions; gross cap 100%; vol target 20%; ATR period 20; stop multiple 2N.
- ADAPTATION (must be disclosed with any result): neither component publishes a hard stop, so 2 x ATR(20) is used as the exit-distance proxy. This is our choice, not a published parameter.

## IDEA-110 — Levered Risk Layer (targets SPY's trailing volatility)
- Exact rule: As IDEA-109, but the book scale factor targets SPY's own trailing 20-day annualized realized volatility instead of a fixed 20%: leverage L(t) = SPY_realized_vol(t) / book_realized_vol(t), capped at 3.0x and floored at 0.25x. Gross exposure above 1.0x pays financing (T-bill + 150bps on the borrowed fraction, per engine cost rules); shorts pay borrow. All costs always on.
- Allowed settings: same risk_pct grid; leverage cap 3.0x; vol windows 20d.
- Pass criteria: PASS-STD, reported against SPY and QQQ buy-and-hold on each era.

**Batch 5 — logged 2026-08-23 17:47 EDT. System controls, not tradeable strategies (no variant registrations).**

## CONTROL-001 — Kill Switch (halt rules)
- Authority file: `research/HALT_RULES.yaml` (rev 2). Thresholds change ONLY by the owner editing that file; no code path writes to it, and its SHA-256 + revision are stamped into every daily log line.
- Rule 1 (skill): rolling 63d and 252d live return vs a Monte Carlo null of random-entry paths matched on time-in-market and switch count, applied to the same realized market returns. Halt below the 5th percentile. Power guards: no halt if the shortfall vs the random median is < 3% (noise), and if the null spread is < 2% the percentile is meaningless so a material shortfall halts on the shortfall itself (attributed to drag/cost/tracking, not timing).
- Rule 2 (drawdown): warn at 1.0x and halt at 1.2x the worst backtest drawdown of the deployed config (default 0.333 = IDEA-109 unlevered @0.75%, 2001-2009, variant [0217]).
- Halt blocks NEW entries only; existing positions follow normal exits. No auto-resume under any condition; clearing requires a hand-written token in HALT_STATE.json. Missing/malformed rules or unreadable state fail CLOSED.
- DESIGN DEFECT FOUND AND FIXED before go-live: rev 1 produced a FALSE HALT on a dry run of the healthy 2001-2009 book (live +17.38% vs random median +17.47% scored 0.0th percentile) because an always-invested book collapses the null to a point mass. Fixed in rev 2 by the two power guards above; regression tests `test_no_halt_when_null_collapses` and `test_still_halts_on_a_material_shortfall` lock the behaviour in.
