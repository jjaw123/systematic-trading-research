# VARIANT LEDGER — Append-Only Count of Every Variant Ever Tested

**Policy (fixed, applies to this file forever):**
1. Every specific variant (idea + exact asset(s) + exact settings + exact test period) gets a numbered REGISTERED line here BEFORE its backtest runs. No registration, no test.
2. Lines are NEVER edited or deleted. Results are appended as a new RESULT line carrying the same variant number.
3. The running count of variants ever tested = the highest variant number in this file.
4. Ideas must already exist in `IDEA_LOG.md` before any variant of them can be registered here.
5. Verdict is PASS only if the variant beats dividend-adjusted buy-and-hold of the same asset(s) over the same period on BOTH total return AND max drawdown ("PASS-STD" in IDEA_LOG.md).

**Line format:**
```
[NNNN] <timestamp> | REGISTERED | <IDEA-ID> | <asset(s)> | <exact settings> | <test period> | pending
[NNNN] <timestamp> | RESULT     | return: X% vs B&H Y% | maxDD: X% vs B&H Y% | <PASS|FAIL> | <notes>
```

**RUNNING COUNT: highest [NNNN] below. No variants registered yet as of 2026-08-23 16:16 EDT.**

---
*(Append entries below this line. Never modify anything above it.)*
[0001] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-001 | SPY | SMA50>SMA200 long/flat, daily | 2010-01-01..2022-12-31 | pending
[0001] 2026-08-23 17:10:25  EDT | RESULT | return +144.8% vs B&H +333.8% | maxDD -32.0% vs B&H -32.0% | FAIL | Sharpe 0.53, trades/yr 1.0
[0002] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-001 | QQQ | SMA50>SMA200 long/flat, daily | 2010-01-01..2022-12-31 | pending
[0002] 2026-08-23 17:10:25  EDT | RESULT | return +387.2% vs B&H +542.9% | maxDD -27.6% vs B&H -36.7% | FAIL | Sharpe 0.75, trades/yr 1.2
[0003] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-001 | GLD | SMA50>SMA200 long/flat, daily | 2010-01-01..2022-12-31 | pending
[0003] 2026-08-23 17:10:25  EDT | RESULT | return +43.8% vs B&H +54.1% | maxDD -36.2% vs B&H -45.3% | FAIL | Sharpe 0.24, trades/yr 1.5
[0004] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-002 | SPY | close>SMA200 long/cash, daily | 2010-01-01..2022-12-31 | pending
[0004] 2026-08-23 17:10:25  EDT | RESULT | return +145.5% vs B&H +333.8% | maxDD -24.4% vs B&H -32.0% | FAIL | Sharpe 0.59, trades/yr 5.8
[0005] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-002 | EFA | close>SMA200 long/cash, daily | 2010-01-01..2022-12-31 | pending
[0005] 2026-08-23 17:10:25  EDT | RESULT | return +37.8% vs B&H +71.3% | maxDD -24.0% vs B&H -34.0% | FAIL | Sharpe 0.22, trades/yr 9.6
[0006] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-002 | GLD | close>SMA200 long/cash, daily | 2010-01-01..2022-12-31 | pending
[0006] 2026-08-23 17:10:25  EDT | RESULT | return +27.5% vs B&H +54.1% | maxDD -33.7% vs B&H -45.3% | FAIL | Sharpe 0.17, trades/yr 9.6
[0007] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-002 | VNQ | close>SMA200 long/cash, daily | 2010-01-01..2022-12-31 | pending
[0007] 2026-08-23 17:10:25  EDT | RESULT | return +70.7% vs B&H +202.5% | maxDD -26.5% vs B&H -39.9% | FAIL | Sharpe 0.32, trades/yr 9.2
[0008] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-003 | SPY | 12m return>0 at month-end, hold 1 month | 2010-01-01..2022-12-31 | pending
[0008] 2026-08-23 17:10:25  EDT | RESULT | return +214.1% vs B&H +333.8% | maxDD -32.0% vs B&H -32.0% | FAIL | Sharpe 0.61, trades/yr 0.7
[0009] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-003 | GLD | 12m return>0 at month-end, hold 1 month | 2010-01-01..2022-12-31 | pending
[0009] 2026-08-23 17:10:25  EDT | RESULT | return +42.6% vs B&H +54.1% | maxDD -32.2% vs B&H -45.3% | FAIL | Sharpe 0.24, trades/yr 1.8
[0010] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-004 | 9 SPDR sectors | rank t-12..t-1 return monthly, top 1 of 9 (=top decile), EW | 2010-01-01..2022-12-31 | pending
[0010] 2026-08-23 17:10:25  EDT | RESULT | ERROR (ValueError): Encountered all NA values
[0011] 2026-08-23 17:10:25  EDT | REGISTERED | IDEA-005 | SPY/EFA/AGG | 12m relative SPY vs EFA + absolute>0 else AGG, monthly | 2010-01-01..2022-12-31 | pending
[0011] 2026-08-23 17:10:34  EDT | RESULT | return +127.1% vs B&H +126.0% | maxDD -32.0% vs B&H -23.7% | FAIL | Sharpe 0.44, trades/yr 1.5
[0012] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-006 | SPY | MACD>signal long/flat, daily | 2010-01-01..2022-12-31 | pending
[0012] 2026-08-23 17:10:34  EDT | RESULT | return +110.8% vs B&H +333.8% | maxDD -15.9% vs B&H -32.0% | FAIL | Sharpe 0.55, trades/yr 20.7
[0013] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-006 | GLD | MACD>signal long/flat, daily | 2010-01-01..2022-12-31 | pending
[0013] 2026-08-23 17:10:34  EDT | RESULT | return +27.4% vs B&H +54.1% | maxDD -27.7% vs B&H -45.3% | FAIL | Sharpe 0.17, trades/yr 20.3
[0014] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-007 | GLD | AF 0.02/0.02/0.20, long/short flip | 2010-01-01..2022-12-31 | pending
[0014] 2026-08-23 17:10:34  EDT | RESULT | return +34.4% vs B&H +54.1% | maxDD -40.2% vs B&H -45.3% | FAIL | Sharpe 0.19, trades/yr 20.4
[0015] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-008 | GLD | EMA4>EMA9>EMA18 long/flat | 2010-01-01..2022-12-31 | pending
[0015] 2026-08-23 17:10:34  EDT | RESULT | return +39.9% vs B&H +54.1% | maxDD -25.5% vs B&H -45.3% | FAIL | Sharpe 0.25, trades/yr 18.4
[0016] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-008 | SPY | EMA4>EMA9>EMA18 long/flat | 2010-01-01..2022-12-31 | pending
[0016] 2026-08-23 17:10:34  EDT | RESULT | return +67.8% vs B&H +333.8% | maxDD -16.0% vs B&H -32.0% | FAIL | Sharpe 0.41, trades/yr 20.6
[0017] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-009 | 9 SPDR sectors | EW sectors within 5% of 252d high, monthly rebalance | ADAPT: monthly rebalance instead of 6-mo tranche holding | 2010-01-01..2022-12-31 | pending
[0017] 2026-08-23 17:10:34  EDT | RESULT | return +159.0% vs B&H +342.7% | maxDD -31.8% vs B&H -34.6% | FAIL | Sharpe 0.56, trades/yr 9.1
[0018] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-010 | GLD | +DI x-above -DI & ADX14>25 entry; opposite DI cross exit | 2010-01-01..2022-12-31 | pending
[0018] 2026-08-23 17:10:34  EDT | RESULT | return +5.0% vs B&H +54.1% | maxDD -8.5% vs B&H -45.3% | FAIL | Sharpe -0.06, trades/yr 2.9
[0019] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-045 | GLD | SMA10>SMA30 long/flat | 2010-01-01..2022-12-31 | pending
[0019] 2026-08-23 17:10:34  EDT | RESULT | return +33.5% vs B&H +54.1% | maxDD -30.9% vs B&H -45.3% | FAIL | Sharpe 0.20, trades/yr 10.1
[0020] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-045 | SPY | SMA10>SMA30 long/flat | 2010-01-01..2022-12-31 | pending
[0020] 2026-08-23 17:10:34  EDT | RESULT | return +83.4% vs B&H +333.8% | maxDD -16.5% vs B&H -32.0% | FAIL | Sharpe 0.42, trades/yr 8.1
[0021] 2026-08-23 17:10:34  EDT | REGISTERED | IDEA-046 | SPY | SMA5>SMA20>SMA50 long/flat | 2010-01-01..2022-12-31 | pending
[0021] 2026-08-23 17:10:35  EDT | RESULT | return +51.3% vs B&H +333.8% | maxDD -22.8% vs B&H -32.0% | FAIL | Sharpe 0.34, trades/yr 12.1
[0022] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-047 | SPY (SHY cash) | 12m SPY return > 12m SHY return else SHY, monthly | 2010-01-01..2022-12-31 | pending
[0022] 2026-08-23 17:10:35  EDT | RESULT | return +111.8% vs B&H +333.8% | maxDD -38.0% vs B&H -32.0% | FAIL | Sharpe 0.42, trades/yr 1.2
[0023] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-048 | SPY/EFA/GLD/IEF (SHY cash) | top 12m of 4 if > SHY 12m else SHY, monthly | 2010-01-01..2022-12-31 | pending
[0023] 2026-08-23 17:10:35  EDT | RESULT | ERROR (ValueError): Encountered all NA values
[0024] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-049 | SPY/VEU/AGG/VNQ/GLD | 20% sleeves, each on only if close>SMA200, monthly | 2010-01-01..2022-12-31 | pending
[0024] 2026-08-23 17:10:35  EDT | RESULT | return +66.7% vs B&H +132.3% | maxDD -10.0% vs B&H -23.6% | FAIL | Sharpe 0.50, trades/yr 6.5
[0025] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-050 | SPY | GC long only while ADX14>=25 | 2010-01-01..2022-12-31 | pending
[0025] 2026-08-23 17:10:35  EDT | RESULT | return +34.5% vs B&H +333.8% | maxDD -25.8% vs B&H -32.0% | FAIL | Sharpe 0.22, trades/yr 6.8
[0026] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-051 | GLD | close>EMA20+2xATR10 entry; close<EMA20 exit | 2010-01-01..2022-12-31 | pending
[0026] 2026-08-23 17:10:35  EDT | RESULT | return +22.5% vs B&H +54.1% | maxDD -18.9% vs B&H -45.3% | FAIL | Sharpe 0.16, trades/yr 7.2
[0027] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-052 | GLD | Up>70 & Down<30 entry; Up<50 exit | 2010-01-01..2022-12-31 | pending
[0027] 2026-08-23 17:10:35  EDT | RESULT | return +8.8% vs B&H +54.1% | maxDD -37.9% vs B&H -45.3% | FAIL | Sharpe 0.06, trades/yr 8.9
[0028] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-053 | SPY | 125d ROC>0 long/flat | 2010-01-01..2022-12-31 | pending
[0028] 2026-08-23 17:10:35  EDT | RESULT | return +160.5% vs B&H +333.8% | maxDD -23.2% vs B&H -32.0% | FAIL | Sharpe 0.63, trades/yr 6.5
[0029] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-054 | SPY | month-end close > SMA10 of month-end closes | 2010-01-01..2022-12-31 | pending
[0029] 2026-08-23 17:10:35  EDT | RESULT | return +117.9% vs B&H +333.8% | maxDD -22.2% vs B&H -32.0% | FAIL | Sharpe 0.47, trades/yr 1.7
[0030] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-054 | GLD | month-end close > SMA10 of month-end closes | 2010-01-01..2022-12-31 | pending
[0030] 2026-08-23 17:10:35  EDT | RESULT | return +22.8% vs B&H +54.1% | maxDD -41.6% vs B&H -45.3% | FAIL | Sharpe 0.14, trades/yr 2.2
[0031] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-055 | SPY | SMA10w>SMA40w of completed weekly closes | 2010-01-01..2022-12-31 | pending
[0031] 2026-08-23 17:10:35  EDT | RESULT | return +141.3% vs B&H +333.8% | maxDD -32.0% vs B&H -32.0% | FAIL | Sharpe 0.53, trades/yr 1.0
[0032] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-056 | GLD | EMA12>EMA26 long/flat | 2010-01-01..2022-12-31 | pending
[0032] 2026-08-23 17:10:35  EDT | RESULT | return +33.2% vs B&H +54.1% | maxDD -37.1% vs B&H -45.3% | FAIL | Sharpe 0.20, trades/yr 8.6
[0033] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-057 | SPY | weekly MACD gate; enter RSI2<10; exit RSI2>70 | 2010-01-01..2022-12-31 | pending
[0033] 2026-08-23 17:10:35  EDT | RESULT | return +59.4% vs B&H +333.8% | maxDD -10.9% vs B&H -32.0% | FAIL | Sharpe 0.53, trades/yr 10.9
[0034] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-058 | GLD | 20d-high entry; exit close<HH-3xATR22 | 2010-01-01..2022-12-31 | pending
[0034] 2026-08-23 17:10:35  EDT | RESULT | return +36.6% vs B&H +54.1% | maxDD -19.3% vs B&H -45.3% | FAIL | Sharpe 0.24, trades/yr 7.6
[0035] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-059 | GLD | ATR10 mult 3, long/flat | 2010-01-01..2022-12-31 | pending
[0035] 2026-08-23 17:10:35  EDT | RESULT | return +31.6% vs B&H +54.1% | maxDD -20.4% vs B&H -45.3% | FAIL | Sharpe 0.19, trades/yr 9.0
[0036] 2026-08-23 17:10:35  EDT | REGISTERED | IDEA-060 | SPY | 50d regression slope>0 long/flat | 2010-01-01..2022-12-31 | pending
[0036] 2026-08-23 17:10:36  EDT | RESULT | return +107.6% vs B&H +333.8% | maxDD -25.5% vs B&H -32.0% | FAIL | Sharpe 0.48, trades/yr 4.5
[0037] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-062 | SPY | GC entry; exit close<HH-2xATR14; re-enter on fresh cross | 2010-01-01..2022-12-31 | pending
[0037] 2026-08-23 17:10:36  EDT | RESULT | return +20.7% vs B&H +333.8% | maxDD -5.5% vs B&H -32.0% | FAIL | Sharpe 0.33, trades/yr 0.9
[0038] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-063 | GLD | SMA10>20>30>40>50 long/flat | 2010-01-01..2022-12-31 | pending
[0038] 2026-08-23 17:10:36  EDT | RESULT | return +31.1% vs B&H +54.1% | maxDD -20.2% vs B&H -45.3% | FAIL | Sharpe 0.22, trades/yr 6.7
[0039] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-064 | GLD | hold while close>=upper BB(20,2) | 2010-01-01..2022-12-31 | pending
[0039] 2026-08-23 17:10:36  EDT | RESULT | return +13.5% vs B&H +54.1% | maxDD -8.7% vs B&H -45.3% | FAIL | Sharpe 0.11, trades/yr 15.7
[0040] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-065 | SPY | within 5% of 252d high & 3m ret>0; exit 10% off high | 2010-01-01..2022-12-31 | pending
[0040] 2026-08-23 17:10:36  EDT | RESULT | return +170.3% vs B&H +333.8% | maxDD -18.4% vs B&H -32.0% | FAIL | Sharpe 0.65, trades/yr 1.5
[0041] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-065 | AAPL | within 5% of 252d high & 3m ret>0; exit 10% off high | 2010-01-01..2022-12-31 | pending
[0041] 2026-08-23 17:10:36  EDT | RESULT | return +267.2% vs B&H +1875.5% | maxDD -36.1% vs B&H -44.2% | FAIL | Sharpe 0.58, trades/yr 4.4
[0042] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-066 | 9 SPDR sectors | 6m return rank, top 3 EW, monthly | 2010-01-01..2022-12-31 | pending
[0042] 2026-08-23 17:10:36  EDT | RESULT | return +382.9% vs B&H +342.7% | maxDD -29.0% vs B&H -34.6% | PASS | Sharpe 0.77, trades/yr 8.0
[0043] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-102 | 9 SPDR sectors | top 3 by 6m return, weights 1/vol20 normalized, monthly | 2010-01-01..2022-12-31 | pending
[0043] 2026-08-23 17:10:36  EDT | RESULT | return +344.8% vs B&H +342.7% | maxDD -29.0% vs B&H -34.6% | PASS | Sharpe 0.75, trades/yr 12.0
[0044] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-067 | SPY | 12m ret/12m vol > 0.3 at month-end | 2010-01-01..2022-12-31 | pending
[0044] 2026-08-23 17:10:36  EDT | RESULT | return +68.4% vs B&H +333.8% | maxDD -39.0% vs B&H -32.0% | FAIL | Sharpe 0.31, trades/yr 1.9
[0045] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-011 | SPY | RSI2<10 & close>SMA200 entry; RSI2>70 or close>SMA5 exit | 2010-01-01..2022-12-31 | pending
[0045] 2026-08-23 17:10:36  EDT | RESULT | return +53.2% vs B&H +333.8% | maxDD -14.2% vs B&H -32.0% | FAIL | Sharpe 0.43, trades/yr 15.6
[0046] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-011 | QQQ | RSI2<10 & close>SMA200 entry; RSI2>70 or close>SMA5 exit | 2010-01-01..2022-12-31 | pending
[0046] 2026-08-23 17:10:36  EDT | RESULT | return +50.6% vs B&H +542.9% | maxDD -12.7% vs B&H -36.7% | FAIL | Sharpe 0.34, trades/yr 16.6
[0047] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-012 | SPY | close<lower BB(20,2) entry; close>=SMA20 exit | 2010-01-01..2022-12-31 | pending
[0047] 2026-08-23 17:10:36  EDT | RESULT | return +98.9% vs B&H +333.8% | maxDD -27.0% vs B&H -32.0% | FAIL | Sharpe 0.48, trades/yr 9.2
[0048] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-014 | SPY | IBS<0.2 entry, 1-day hold (re-signal extends) | ADAPT: exit at next open instead of next close per protocol | 2010-01-01..2022-12-31 | pending
[0048] 2026-08-23 17:10:36  EDT | RESULT | return +71.3% vs B&H +333.8% | maxDD -20.2% vs B&H -32.0% | FAIL | Sharpe 0.43, trades/yr 70.2 | 2x: +42.8% 3x: +19.0%
[0049] 2026-08-23 17:10:36  EDT | REGISTERED | IDEA-014 | GLD | IBS<0.2 entry, 1-day hold (re-signal extends) | ADAPT: exit at next open instead of next close per protocol | 2010-01-01..2022-12-31 | pending
[0049] 2026-08-23 17:10:37  EDT | RESULT | return -7.6% vs B&H +54.1% | maxDD -23.8% vs B&H -45.3% | FAIL | Sharpe -0.14, trades/yr 72.9 | 2x: -23.5% 3x: -36.7%
[0050] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-015 | SPY | %R14<-90 entry; %R14>-50 exit | 2010-01-01..2022-12-31 | pending
[0050] 2026-08-23 17:10:37  EDT | RESULT | return +76.0% vs B&H +333.8% | maxDD -24.1% vs B&H -32.0% | FAIL | Sharpe 0.42, trades/yr 11.6
[0051] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-016 | SPY | short when close>SMA20+5%; cover at SMA20 | 2010-01-01..2022-12-31 | pending
[0051] 2026-08-23 17:10:37  EDT | RESULT | return +0.6% vs B&H +333.8% | maxDD -9.3% vs B&H -32.0% | FAIL | Sharpe -0.11, trades/yr 1.4
[0052] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-018 | SPY | %K(14)x%D(3) below 20 entry; cross below above 80 exit | 2010-01-01..2022-12-31 | pending
[0052] 2026-08-23 17:10:37  EDT | RESULT | return +118.2% vs B&H +333.8% | maxDD -25.8% vs B&H -32.0% | FAIL | Sharpe 0.51, trades/yr 11.8
[0053] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-019 | GLD/SLV | 60d ratio z; enter |z|>2 (0.5/-0.5); exit z=0 | 2010-01-01..2022-12-31 | pending
[0053] 2026-08-23 17:10:37  EDT | RESULT | return -18.8% vs B&H +49.8% | maxDD -29.6% vs B&H -57.5% | FAIL | Sharpe -0.24, trades/yr 6.9
[0054] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-019 | XLE/XLB | 60d ratio z; enter |z|>2 (0.5/-0.5); exit z=0 | 2010-01-01..2022-12-31 | pending
[0054] 2026-08-23 17:10:37  EDT | RESULT | return -16.6% vs B&H +182.6% | maxDD -31.9% vs B&H -51.8% | FAIL | Sharpe -0.20, trades/yr 7.5
[0055] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-068 | SPY | 7d low close & >SMA200 entry; 7d high close exit | 2010-01-01..2022-12-31 | pending
[0055] 2026-08-23 17:10:37  EDT | RESULT | return +96.6% vs B&H +333.8% | maxDD -14.7% vs B&H -32.0% | FAIL | Sharpe 0.52, trades/yr 20.5
[0056] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-069 | SPY | 3d avg PctRank(100)<15 & >SMA200; exit >70 | 2010-01-01..2022-12-31 | pending
[0056] 2026-08-23 17:10:37  EDT | RESULT | return +30.6% vs B&H +333.8% | maxDD -20.3% vs B&H -32.0% | FAIL | Sharpe 0.27, trades/yr 1.1
[0057] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-070 | SPY | %R14<-90 & >SMA200; exit %R>-20 | 2010-01-01..2022-12-31 | pending
[0057] 2026-08-23 17:10:37  EDT | RESULT | return +87.2% vs B&H +333.8% | maxDD -29.2% vs B&H -32.0% | FAIL | Sharpe 0.52, trades/yr 6.9
[0058] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-071 | SPY | %K(14,3) x-above 20 & >SMA200; exit x-below 80 | 2010-01-01..2022-12-31 | pending
[0058] 2026-08-23 17:10:37  EDT | RESULT | return +85.1% vs B&H +333.8% | maxDD -25.9% vs B&H -32.0% | FAIL | Sharpe 0.52, trades/yr 5.7
[0059] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-072 | SPY | RSI3<10 & close>SMA200; exit RSI3>70 or close>SMA5 | 2010-01-01..2022-12-31 | pending
[0059] 2026-08-23 17:10:37  EDT | RESULT | return +5.6% vs B&H +333.8% | maxDD -13.5% vs B&H -32.0% | FAIL | Sharpe -0.02, trades/yr 5.5
[0060] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-072 | SPY | RSI4<10 & close>SMA200; exit RSI4>70 or close>SMA5 | 2010-01-01..2022-12-31 | pending
[0060] 2026-08-23 17:10:37  EDT | RESULT | return +20.0% vs B&H +333.8% | maxDD -8.1% vs B&H -32.0% | FAIL | Sharpe 0.25, trades/yr 1.8
[0061] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-073 | SPY | close<=0.95xSMA20 & >SMA200; exit at SMA20 | 2010-01-01..2022-12-31 | pending
[0061] 2026-08-23 17:10:37  EDT | RESULT | return +3.9% vs B&H +333.8% | maxDD -27.0% vs B&H -32.0% | FAIL | Sharpe -0.01, trades/yr 0.8
[0062] 2026-08-23 17:10:37  EDT | REGISTERED | IDEA-074 | SPY | RSI2 entries only while ADX14<20 | 2010-01-01..2022-12-31 | pending
[0062] 2026-08-23 17:10:38  EDT | RESULT | return +10.6% vs B&H +333.8% | maxDD -14.6% vs B&H -32.0% | FAIL | Sharpe 0.06, trades/yr 8.3
[0063] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-075 | SPY | 3 lower closes & >SMA200; exit 2 higher closes | 2010-01-01..2022-12-31 | pending
[0063] 2026-08-23 17:10:38  EDT | RESULT | return +45.0% vs B&H +333.8% | maxDD -30.7% vs B&H -32.0% | FAIL | Sharpe 0.30, trades/yr 16.0
[0064] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-076 | AAPL | new 252d intraday low, close back above prior low; hold 5d or exit on fresh low | 2010-01-01..2022-12-31 | pending
[0064] 2026-08-23 17:10:38  EDT | RESULT | return +14.8% vs B&H +1875.5% | maxDD -3.6% vs B&H -44.2% | FAIL | Sharpe 0.19, trades/yr 0.3
[0065] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-076 | MSFT | new 252d intraday low, close back above prior low; hold 5d or exit on fresh low | 2010-01-01..2022-12-31 | pending
[0065] 2026-08-23 17:10:38  EDT | RESULT | return +24.5% vs B&H +916.3% | maxDD -4.3% vs B&H -36.5% | FAIL | Sharpe 0.37, trades/yr 0.8
[0066] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-077 | SPY | close<EMA20-2xATR10 & ADX<20; exit EMA20 | 2010-01-01..2022-12-31 | pending
[0066] 2026-08-23 17:10:38  EDT | RESULT | return +36.3% vs B&H +333.8% | maxDD -10.2% vs B&H -32.0% | FAIL | Sharpe 0.31, trades/yr 3.5
[0067] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-078 | SPY | fade 20d channel touches toward midline while ADX<20 | 2010-01-01..2022-12-31 | pending
[0067] 2026-08-23 17:10:38  EDT | RESULT | return -39.7% vs B&H +333.8% | maxDD -44.0% vs B&H -32.0% | FAIL | Sharpe -0.37, trades/yr 16.6
[0068] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-079 | SPY (VIX signal) | VIX close>1.2x its SMA10 entry; exit VIX<SMA10 | 2010-01-01..2022-12-31 | pending
[0068] 2026-08-23 17:10:38  EDT | RESULT | return +3.0% vs B&H +333.8% | maxDD -31.5% vs B&H -32.0% | FAIL | Sharpe 0.00, trades/yr 9.7
[0069] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-020 | GLD | entry close>20d high; exit close<10d low | 2010-01-01..2022-12-31 | pending
[0069] 2026-08-23 17:10:38  EDT | RESULT | return +40.2% vs B&H +54.1% | maxDD -21.6% vs B&H -45.3% | FAIL | Sharpe 0.25, trades/yr 7.9
[0070] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-021 | GLD | entry close>55d high; exit close<20d low | 2010-01-01..2022-12-31 | pending
[0070] 2026-08-23 17:10:38  EDT | RESULT | return +12.9% vs B&H +54.1% | maxDD -32.7% vs B&H -45.3% | FAIL | Sharpe 0.08, trades/yr 3.9
[0071] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-020 | SPY | entry close>20d high; exit close<10d low | 2010-01-01..2022-12-31 | pending
[0071] 2026-08-23 17:10:38  EDT | RESULT | return +169.4% vs B&H +333.8% | maxDD -8.0% vs B&H -32.0% | FAIL | Sharpe 0.81, trades/yr 8.4
[0072] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-021 | SPY | entry close>55d high; exit close<20d low | 2010-01-01..2022-12-31 | pending
[0072] 2026-08-23 17:10:38  EDT | RESULT | return +44.3% vs B&H +333.8% | maxDD -16.6% vs B&H -32.0% | FAIL | Sharpe 0.30, trades/yr 5.5
[0073] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-022 | AAPL | new 252d close high entry; close<SMA50 exit | 2010-01-01..2022-12-31 | pending
[0073] 2026-08-23 17:10:38  EDT | RESULT | return +334.3% vs B&H +1875.5% | maxDD -29.7% vs B&H -44.2% | FAIL | Sharpe 0.75, trades/yr 3.9
[0074] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-022 | XLK | new 252d close high entry; close<SMA50 exit | 2010-01-01..2022-12-31 | pending
[0074] 2026-08-23 17:10:38  EDT | RESULT | return +37.7% vs B&H +545.9% | maxDD -22.7% vs B&H -35.5% | FAIL | Sharpe 0.23, trades/yr 5.6
[0075] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-023 | GLD | close>prior close+1.5xATR14 long; mirror short; flip on opposite | 2010-01-01..2022-12-31 | pending
[0075] 2026-08-23 17:10:38  EDT | RESULT | return -49.1% vs B&H +54.1% | maxDD -73.2% vs B&H -45.3% | FAIL | Sharpe -0.30, trades/yr 9.2
[0076] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-024 | GLD | bandwidth at 126d low arms 5d; entry close>upper; exit close<SMA20 | ADAPT: squeeze arms entries for 5 days after bandwidth low | 2010-01-01..2022-12-31 | pending
[0076] 2026-08-23 17:10:38  EDT | RESULT | return +6.7% vs B&H +54.1% | maxDD -9.8% vs B&H -45.3% | FAIL | Sharpe -0.02, trades/yr 1.4
[0077] 2026-08-23 17:10:38  EDT | REGISTERED | IDEA-026 | AAPL | 20d high close & vol>1.5x50d avg; exit 10d low | ADAPT: exit from 150-list #78 (source gave no exit) | 2010-01-01..2022-12-31 | pending
[0077] 2026-08-23 17:10:39  EDT | RESULT | return +52.8% vs B&H +1875.5% | maxDD -34.2% vs B&H -44.2% | FAIL | Sharpe 0.27, trades/yr 4.3
[0078] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-026 | MSFT | 20d high close & vol>1.5x50d avg; exit 10d low | ADAPT: exit from 150-list #78 (source gave no exit) | 2010-01-01..2022-12-31 | pending
[0078] 2026-08-23 17:10:39  EDT | RESULT | return +20.3% vs B&H +916.3% | maxDD -18.5% vs B&H -36.5% | FAIL | Sharpe 0.13, trades/yr 5.2
[0079] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-061 | GLD | long close>20d high; flip short close<20d low | 2010-01-01..2022-12-31 | pending
[0079] 2026-08-23 17:10:39  EDT | RESULT | return -33.2% vs B&H +54.1% | maxDD -47.3% vs B&H -45.3% | FAIL | Sharpe -0.16, trades/yr 6.2
[0080] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-080 | GLD | range>1.5xATR10 & close top third; 1-day hold | 2010-01-01..2022-12-31 | pending
[0080] 2026-08-23 17:10:39  EDT | RESULT | return +16.1% vs B&H +54.1% | maxDD -2.9% vs B&H -45.3% | FAIL | Sharpe 0.29, trades/yr 10.3
[0081] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-081 | GLD | close>prior close+2xATR20; exit close<HH-2xATR20 | 2010-01-01..2022-12-31 | pending
[0081] 2026-08-23 17:10:39  EDT | RESULT | return +16.1% vs B&H +54.1% | maxDD -14.0% vs B&H -45.3% | FAIL | Sharpe 0.12, trades/yr 5.0
[0082] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-082 | GLD | 20d range<50% of 20d-ago range; entry close>20d high; exit 10d low | 2010-01-01..2022-12-31 | pending
[0082] 2026-08-23 17:10:39  EDT | RESULT | return -7.0% vs B&H +54.1% | maxDD -24.8% vs B&H -45.3% | FAIL | Sharpe -0.21, trades/yr 2.1
[0083] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-083 | GLD | >=8%/10d impulse; 3-10d tight flag (<50% impulse ADR); entry close>flag high; stop flag low | 2010-01-01..2022-12-31 | pending
[0083] 2026-08-23 17:10:39  EDT | RESULT | return +8.2% vs B&H +54.1% | maxDD -0.0% vs B&H -45.3% | FAIL | Sharpe 0.00, trades/yr 0.0
[0084] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-084 | AAPL | 20d close high & OBV 20d high; exit 10d low | 2010-01-01..2022-12-31 | pending
[0084] 2026-08-23 17:10:39  EDT | RESULT | return +648.4% vs B&H +1875.5% | maxDD -32.7% vs B&H -44.2% | FAIL | Sharpe 0.94, trades/yr 7.2
[0085] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-084 | MSFT | 20d close high & OBV 20d high; exit 10d low | 2010-01-01..2022-12-31 | pending
[0085] 2026-08-23 17:10:39  EDT | RESULT | return +74.2% vs B&H +916.3% | maxDD -24.8% vs B&H -36.5% | FAIL | Sharpe 0.32, trades/yr 7.9
[0086] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-085 | GLD | swing = peak with >=3% pullback; entry close>swing high; stop pullback low | 2010-01-01..2022-12-31 | pending
[0086] 2026-08-23 17:10:39  EDT | RESULT | return +8.2% vs B&H +54.1% | maxDD -0.0% vs B&H -45.3% | FAIL | Sharpe 0.00, trades/yr 0.0
[0087] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-086 | GLD | close>126d high with prior range<15%; exit 60d low | 2010-01-01..2022-12-31 | pending
[0087] 2026-08-23 17:10:39  EDT | RESULT | return +7.8% vs B&H +54.1% | maxDD -34.5% vs B&H -45.3% | FAIL | Sharpe 0.05, trades/yr 1.9
[0088] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-087 | SPY | close>prior year high close; exit close<prior year low close | 2010-01-01..2022-12-31 | pending
[0088] 2026-08-23 17:10:39  EDT | RESULT | return +156.5% vs B&H +333.8% | maxDD -36.8% vs B&H -32.0% | FAIL | Sharpe 0.50, trades/yr 0.5
[0089] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-088 | GLD | close>NR7 high entry; exit close<NR7 low | ADAPT: close-confirmation entry replaces intraday stop order | 2010-01-01..2022-12-31 | pending
[0089] 2026-08-23 17:10:39  EDT | RESULT | return +23.8% vs B&H +54.1% | maxDD -20.8% vs B&H -45.3% | FAIL | Sharpe 0.15, trades/yr 30.0
[0090] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-089 | GLD | >SMA200; 2-3 down-day pullback; entry close>pre-pullback high; stop pullback low | ADAPT: anchor = high of bar preceding the pullback streak | 2010-01-01..2022-12-31 | pending
[0090] 2026-08-23 17:10:39  EDT | RESULT | return +7.6% vs B&H +54.1% | maxDD -29.0% vs B&H -45.3% | FAIL | Sharpe 0.05, trades/yr 9.4
[0091] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-028 | SPY | long Nov1-Apr30, flat May-Oct | 2010-01-01..2022-12-31 | pending
[0091] 2026-08-23 17:10:39  EDT | RESULT | return +163.4% vs B&H +333.8% | maxDD -32.0% vs B&H -32.0% | FAIL | Sharpe 0.64, trades/yr 2.0
[0092] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-029 | SPY | long last trading day through 3rd of next month | 2010-01-01..2022-12-31 | pending
[0092] 2026-08-23 17:10:39  EDT | RESULT | return +53.6% vs B&H +333.8% | maxDD -15.0% vs B&H -32.0% | FAIL | Sharpe 0.40, trades/yr 24.0
[0093] 2026-08-23 17:10:39  EDT | REGISTERED | IDEA-029 | QQQ | long last trading day through 3rd of next month | 2010-01-01..2022-12-31 | pending
[0093] 2026-08-23 17:10:40  EDT | RESULT | return +62.8% vs B&H +542.9% | maxDD -19.9% vs B&H -36.7% | FAIL | Sharpe 0.39, trades/yr 24.0
[0094] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-030 | SPY | long last 5 days of Dec + first 2 of Jan | 2010-01-01..2022-12-31 | pending
[0094] 2026-08-23 17:10:40  EDT | RESULT | return +14.4% vs B&H +333.8% | maxDD -6.8% vs B&H -32.0% | FAIL | Sharpe 0.19, trades/yr 2.0
[0095] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-031 | GLD | long Sep 1 - end Feb | 2010-01-01..2022-12-31 | pending
[0095] 2026-08-23 17:10:40  EDT | RESULT | return +5.1% vs B&H +54.1% | maxDD -29.2% vs B&H -45.3% | FAIL | Sharpe 0.03, trades/yr 2.0
[0096] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-090 | GLD | long Aug 25 - Oct 31 | 2010-01-01..2022-12-31 | pending
[0096] 2026-08-23 17:10:40  EDT | RESULT | return -11.6% vs B&H +54.1% | maxDD -28.5% vs B&H -45.3% | FAIL | Sharpe -0.20, trades/yr 2.0
[0097] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-032 | SPY | long the trading day before each market holiday | ADAPT: holidays derived from exchange calendar; holds through the holiday-overnight to next open | 2010-01-01..2022-12-31 | pending
[0097] 2026-08-23 17:10:40  EDT | RESULT | return +14.8% vs B&H +333.8% | maxDD -8.5% vs B&H -32.0% | FAIL | Sharpe 0.16, trades/yr 18.1
[0098] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-091 | SPY | long witching Friday open through following Tuesday open | ADAPT: published Thu-close->Mon-close shifted to open execution | 2010-01-01..2022-12-31 | pending
[0098] 2026-08-23 17:10:40  EDT | RESULT | return -3.5% vs B&H +333.8% | maxDD -11.0% vs B&H -32.0% | FAIL | Sharpe -0.27, trades/yr 8.0
[0099] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-033 | 9 SPDR sectors | last 5 days of quarter, hold top trailing-63d sector | ADAPT: sector universe stands in for S&P500 stocks (no constituent data); top pick refreshed daily in window | 2010-01-01..2022-12-31 | pending
[0099] 2026-08-23 17:10:40  EDT | RESULT | ERROR (ValueError): Encountered all NA values
[0100] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-034 | SPY | expanding >=240-month history; hold top-6 months | ADAPT: GLD ineligible (needs 20y history; GLD data starts 2004) | 2010-01-01..2022-12-31 | pending
[0100] 2026-08-23 17:10:40  EDT | RESULT | return +139.3% vs B&H +333.8% | maxDD -30.1% vs B&H -32.0% | FAIL | Sharpe 0.63, trades/yr 3.6
[0101] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-035+IDEA-041 | GLD (Donchian 20/10) | w=1%/(2xATR20/px) cap 1.0; hard stop entry-2xATR20 | 2010-01-01..2022-12-31 | pending
[0101] 2026-08-23 17:10:40  EDT | RESULT | return +21.7% vs B&H +54.1% | maxDD -8.9% vs B&H -45.3% | FAIL | Sharpe 0.24, trades/yr 90.5 | 2x: +20.3% 3x: +19.0%
[0102] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-036 | GLD (Donchian 20/10) | w=1%/(2xATR20/px) cap 1.0; Donchian exits only | 2010-01-01..2022-12-31 | pending
[0102] 2026-08-23 17:10:40  EDT | RESULT | return +32.2% vs B&H +54.1% | maxDD -10.6% vs B&H -45.3% | FAIL | Sharpe 0.37, trades/yr 102.0 | 2x: +30.7% 3x: +29.1%
[0103] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-037 | GLD (Donchian 20/10) | 0.5x Kelly from own closed trades (>=30), else full size | 2010-01-01..2022-12-31 | pending
[0103] 2026-08-23 17:10:40  EDT | RESULT | return +16.2% vs B&H +54.1% | maxDD -8.7% vs B&H -45.3% | FAIL | Sharpe 0.17, trades/yr 7.9
[0104] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-038 | SPY | w=10%/realized20 ann., weekly, clip [0.25,2] | 2010-01-01..2022-12-31 | pending
[0104] 2026-08-23 17:10:40  EDT | RESULT | return +185.4% vs B&H +333.8% | maxDD -16.4% vs B&H -32.0% | FAIL | Sharpe 0.69, trades/yr 51.2
[0105] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-039 | SPY/GLD/XLE/XLK/XLV | 20% each, monthly rebalance; benchmark = same basket unrebalanced | 2010-01-01..2022-12-31 | pending
[0105] 2026-08-23 17:10:40  EDT | RESULT | return +295.4% vs B&H +295.3% | maxDD -30.5% vs B&H -30.5% | PASS | Sharpe 0.75, trades/yr 0.0
[0106] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-040 | GLD (Donchian 20/10) | add 0.25 unit per 0.5xATR20 favorable, max 4; per-unit 2N stop | 2010-01-01..2022-12-31 | pending
[0106] 2026-08-23 17:10:40  EDT | RESULT | return +41.5% vs B&H +54.1% | maxDD -15.0% vs B&H -45.3% | FAIL | Sharpe 0.29, trades/yr 16.6
[0107] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-042 | GLD/SPY/QQQ Donchian book | 1/3 base, single cap 25%, corr>0.7 pair sum cap 60% | 2010-01-01..2022-12-31 | pending
[0107] 2026-08-23 17:10:40  EDT | RESULT | return +77.3% vs B&H +281.9% | maxDD -8.0% vs B&H -24.1% | FAIL | Sharpe 0.71, trades/yr 22.2
[0108] 2026-08-23 17:10:40  EDT | REGISTERED | IDEA-044 | GLD/SPY/QQQ Donchian book | scale book so sum(w x 2xATR20/px) <= 6% | 2010-01-01..2022-12-31 | pending
[0108] 2026-08-23 17:10:41  EDT | RESULT | return +106.8% vs B&H +281.9% | maxDD -10.5% vs B&H -24.1% | FAIL | Sharpe 0.71, trades/yr 22.8
[0109] 2026-08-23 17:10:41  EDT | REGISTERED | IDEA-093 | SPY/GLD/IEF | 1/vol60 normalized, monthly | 2010-01-01..2022-12-31 | pending
[0109] 2026-08-23 17:10:41  EDT | RESULT | return +93.7% vs B&H +127.7% | maxDD -17.0% vs B&H -17.4% | FAIL | Sharpe 0.78, trades/yr 12.0
[0110] 2026-08-23 17:10:41  EDT | REGISTERED | IDEA-094 | SPY | alloc=min(1,3x(V-0.9)/V), weekly | ADAPT: equity path approximated pre-cost for the allocation state | 2010-01-01..2022-12-31 | pending
[0110] 2026-08-23 17:10:41  EDT | RESULT | return +334.0% vs B&H +333.8% | maxDD -32.0% vs B&H -32.0% | PASS | Sharpe 0.72, trades/yr 0.0
[0111] 2026-08-23 17:10:41  EDT | REGISTERED | IDEA-095 | GLD (Donchian 20/10) | halve size after 10% strategy DD; restore at new high | ADAPT: strategy equity approximated pre-cost for the DD state | 2010-01-01..2022-12-31 | pending
[0111] 2026-08-23 17:10:41  EDT | RESULT | return +27.1% vs B&H +54.1% | maxDD -17.2% vs B&H -45.3% | FAIL | Sharpe 0.20, trades/yr 8.2
[0112] 2026-08-23 17:10:41  EDT | REGISTERED | IDEA-096 | SPY (VIX signal) | w=20/VIX clip [0.25,1], weekly | 2010-01-01..2022-12-31 | pending
[0112] 2026-08-23 17:10:41  EDT | RESULT | return +236.0% vs B&H +333.8% | maxDD -24.1% vs B&H -32.0% | FAIL | Sharpe 0.70, trades/yr 19.6
[0113] 2026-08-23 17:10:41  EDT | REGISTERED | IDEA-097 | BIL + GLD sleeve | 90% BIL; 10% sleeve on Donchian 20/10 GLD | 2010-01-01..2022-12-31 | pending
[0113] 2026-08-23 17:10:41  EDT | RESULT | return +9.7% vs B&H +32.9% | maxDD -2.5% vs B&H -25.0% | FAIL | Sharpe 0.11, trades/yr 7.9
[0114] 2026-08-23 17:10:41  EDT | REGISTERED | IDEA-098 | SPY/GLD | 60/40 target; rebalance when SPY weight exits [55%,65%] | 2010-01-01..2022-12-31 | pending
[0114] 2026-08-23 17:10:41  EDT | RESULT | return +208.1% vs B&H +180.2% | maxDD -22.3% vs B&H -20.1% | FAIL | Sharpe 0.73, trades/yr 252.0 | 2x: +207.1% 3x: +206.0%
[0115] 2026-08-23 17:11:39 EDT | REGISTERED | IDEA-004 | 9 SPDR sectors | rank t-12..t-1 return monthly, top 1 of 9 (=top decile), EW | 2010-01-01..2022-12-31 | pending (re-run after idxmax warmup-NaN bugfix; supersedes earlier ERROR line)
[0115] 2026-08-23 17:11:39 EDT | RESULT | return +435.9% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.65, trades/yr 3.9
[0116] 2026-08-23 17:11:39 EDT | REGISTERED | IDEA-048 | SPY/EFA/GLD/IEF (SHY cash) | top 12m of 4 if > SHY 12m else SHY, monthly | 2010-01-01..2022-12-31 | pending (re-run after idxmax warmup-NaN bugfix; supersedes earlier ERROR line)
[0116] 2026-08-23 17:11:39 EDT | RESULT | return +23.5% vs B&H +117.7% | maxDD -26.3% vs B&H -20.5% | FAIL | Sharpe 0.14, trades/yr 3.2
[0117] 2026-08-23 17:11:50 EDT | REGISTERED | IDEA-033 | 9 SPDR sectors | last 5 days of quarter, hold top trailing-63d sector | ADAPT: sector universe stands in for S&P500 stocks (no constituent data); top pick refreshed daily in window | 2010-01-01..2022-12-31 | pending (re-run after idxmax warmup-NaN bugfix; supersedes earlier ERROR line)
[0117] 2026-08-23 17:12:32 EDT | REGISTERED | IDEA-033 | 9 SPDR sectors | last 5 days of quarter, hold top trailing-63d sector | ADAPT: sector universe stands in for S&P500 stocks (no constituent data); top pick refreshed daily in window | 2010-01-01..2022-12-31 | pending (re-run 2: first run ERROR'd; second attempt caught by automated lookahead check — calendar flag shifted after reindex; fixed to shift on full calendar)
[0117] 2026-08-23 17:12:32 EDT | RESULT | return +10.9% vs B&H +342.7% | maxDD -18.6% vs B&H -34.6% | FAIL | Sharpe 0.06, trades/yr 10.1
[0105] 2026-08-23 17:24 EDT | NOTE | IDEA-039 PASS verdict DISQUALIFIED as engine artifact: margin +0.16pp with identical maxDD. Causes: (a) benchmark charged terminal exit cost the strategy is not charged; (b) constant-weight portfolios incur zero modeled maintenance turnover (engine charges only weight CHANGES; holding fixed weights trades daily in reality). Treat as FAIL pending engine fix (symmetric terminal liquidation cost + drift-turnover for fixed-weight books).
[0110] 2026-08-23 17:24 EDT | NOTE | IDEA-094 PASS verdict DISQUALIFIED as engine artifact: CPPI state loop starts at 1993 data start, so cushion saturates alloc=1.0 through the whole 2010-2022 eval window - strategy degenerates to buy-and-hold and "wins" only by the same cost asymmetry as [0105]. Treat as FAIL. Re-test requires anchoring the floor at eval-window start (new variant).
[0118] 2026-08-23 17:17:37 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top1 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0118] 2026-08-23 17:17:37 EDT | RESULT | return +51.1% vs B&H +37.9% | maxDD -48.8% vs B&H -52.6% | PASS | Sharpe 0.19, trades/yr 4.6
[0119] 2026-08-23 17:17:37 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top1 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0119] 2026-08-23 17:17:37 EDT | RESULT | return +419.5% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.67, trades/yr 5.2
[0120] 2026-08-23 17:17:37 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top1 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0120] 2026-08-23 17:17:37 EDT | RESULT | return +51.1% vs B&H +37.9% | maxDD -48.8% vs B&H -52.6% | PASS | Sharpe 0.19, trades/yr 4.6
[0121] 2026-08-23 17:17:37 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top1 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0121] 2026-08-23 17:17:37 EDT | RESULT | return +419.5% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.67, trades/yr 5.2
[0122] 2026-08-23 17:17:37 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top2 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0122] 2026-08-23 17:17:37 EDT | RESULT | return +37.7% vs B&H +37.9% | maxDD -48.6% vs B&H -52.6% | FAIL | Sharpe 0.14, trades/yr 7.3
[0123] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top2 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0123] 2026-08-23 17:17:38 EDT | RESULT | return +366.5% vs B&H +342.7% | maxDD -27.7% vs B&H -34.6% | PASS | Sharpe 0.71, trades/yr 7.0
[0124] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top2 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0124] 2026-08-23 17:17:38 EDT | RESULT | return +21.1% vs B&H +37.9% | maxDD -51.2% vs B&H -52.6% | FAIL | Sharpe 0.08, trades/yr 12.0
[0125] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top2 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0125] 2026-08-23 17:17:38 EDT | RESULT | return +327.6% vs B&H +342.7% | maxDD -27.2% vs B&H -34.6% | FAIL | Sharpe 0.69, trades/yr 12.0
[0126] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top3 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0126] 2026-08-23 17:17:38 EDT | RESULT | return +39.1% vs B&H +37.9% | maxDD -49.7% vs B&H -52.6% | PASS | Sharpe 0.14, trades/yr 7.5
[0127] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top3 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0127] 2026-08-23 17:17:38 EDT | RESULT | return +382.9% vs B&H +342.7% | maxDD -29.0% vs B&H -34.6% | PASS | Sharpe 0.77, trades/yr 8.0
[0128] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top3 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0128] 2026-08-23 17:17:38 EDT | RESULT | return +21.2% vs B&H +37.9% | maxDD -50.4% vs B&H -52.6% | FAIL | Sharpe 0.07, trades/yr 12.0
[0129] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=0d top3 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0129] 2026-08-23 17:17:38 EDT | RESULT | return +344.8% vs B&H +342.7% | maxDD -29.0% vs B&H -34.6% | PASS | Sharpe 0.75, trades/yr 12.0
[0130] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top1 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0130] 2026-08-23 17:17:38 EDT | RESULT | return +29.2% vs B&H +37.9% | maxDD -51.6% vs B&H -52.6% | FAIL | Sharpe 0.14, trades/yr 4.9
[0131] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top1 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0131] 2026-08-23 17:17:38 EDT | RESULT | return +427.8% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.67, trades/yr 5.4
[0132] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top1 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0132] 2026-08-23 17:17:38 EDT | RESULT | return +29.2% vs B&H +37.9% | maxDD -51.6% vs B&H -52.6% | FAIL | Sharpe 0.14, trades/yr 4.9
[0133] 2026-08-23 17:17:38 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top1 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0133] 2026-08-23 17:17:38 EDT | RESULT | return +427.8% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.67, trades/yr 5.4
[0134] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top2 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0134] 2026-08-23 17:17:39 EDT | RESULT | return +22.9% vs B&H +37.9% | maxDD -48.1% vs B&H -52.6% | FAIL | Sharpe 0.10, trades/yr 7.5
[0135] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top2 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0135] 2026-08-23 17:17:39 EDT | RESULT | return +420.4% vs B&H +342.7% | maxDD -32.5% vs B&H -34.6% | PASS | Sharpe 0.74, trades/yr 6.5
[0136] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top2 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0136] 2026-08-23 17:17:39 EDT | RESULT | return +10.1% vs B&H +37.9% | maxDD -47.9% vs B&H -52.6% | FAIL | Sharpe 0.05, trades/yr 12.0
[0137] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top2 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0137] 2026-08-23 17:17:39 EDT | RESULT | return +387.8% vs B&H +342.7% | maxDD -32.8% vs B&H -34.6% | PASS | Sharpe 0.72, trades/yr 12.0
[0138] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top3 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0138] 2026-08-23 17:17:39 EDT | RESULT | return +38.0% vs B&H +37.9% | maxDD -43.2% vs B&H -52.6% | PASS | Sharpe 0.13, trades/yr 7.6
[0139] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top3 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0139] 2026-08-23 17:17:39 EDT | RESULT | return +392.9% vs B&H +342.7% | maxDD -29.9% vs B&H -34.6% | PASS | Sharpe 0.76, trades/yr 7.7
[0140] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top3 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0140] 2026-08-23 17:17:39 EDT | RESULT | return +21.8% vs B&H +37.9% | maxDD -41.6% vs B&H -52.6% | FAIL | Sharpe 0.07, trades/yr 12.0
[0141] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=126d skip=21d top3 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0141] 2026-08-23 17:17:39 EDT | RESULT | return +359.2% vs B&H +342.7% | maxDD -29.9% vs B&H -34.6% | PASS | Sharpe 0.75, trades/yr 12.0
[0142] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top1 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0142] 2026-08-23 17:17:39 EDT | RESULT | return +61.4% vs B&H +37.9% | maxDD -50.6% vs B&H -52.6% | PASS | Sharpe 0.22, trades/yr 4.2
[0143] 2026-08-23 17:17:39 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top1 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0143] 2026-08-23 17:17:39 EDT | RESULT | return +446.1% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.68, trades/yr 4.2
[0144] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top1 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0144] 2026-08-23 17:17:40 EDT | RESULT | return +61.4% vs B&H +37.9% | maxDD -50.6% vs B&H -52.6% | PASS | Sharpe 0.22, trades/yr 4.2
[0145] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top1 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0145] 2026-08-23 17:17:40 EDT | RESULT | return +446.1% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.68, trades/yr 4.2
[0146] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top2 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0146] 2026-08-23 17:17:40 EDT | RESULT | return +22.1% vs B&H +37.9% | maxDD -49.2% vs B&H -52.6% | FAIL | Sharpe 0.09, trades/yr 6.6
[0147] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top2 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0147] 2026-08-23 17:17:40 EDT | RESULT | return +322.5% vs B&H +342.7% | maxDD -31.3% vs B&H -34.6% | FAIL | Sharpe 0.66, trades/yr 5.9
[0148] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top2 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0148] 2026-08-23 17:17:40 EDT | RESULT | return +10.3% vs B&H +37.9% | maxDD -48.2% vs B&H -52.6% | FAIL | Sharpe 0.04, trades/yr 12.0
[0149] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top2 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0149] 2026-08-23 17:17:40 EDT | RESULT | return +301.2% vs B&H +342.7% | maxDD -31.5% vs B&H -34.6% | FAIL | Sharpe 0.65, trades/yr 12.0
[0150] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top3 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0150] 2026-08-23 17:17:40 EDT | RESULT | return +11.5% vs B&H +37.9% | maxDD -46.4% vs B&H -52.6% | FAIL | Sharpe 0.04, trades/yr 7.1
[0151] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top3 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0151] 2026-08-23 17:17:40 EDT | RESULT | return +426.9% vs B&H +342.7% | maxDD -28.8% vs B&H -34.6% | PASS | Sharpe 0.80, trades/yr 6.9
[0152] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top3 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0152] 2026-08-23 17:17:40 EDT | RESULT | return -6.8% vs B&H +37.9% | maxDD -45.5% vs B&H -52.6% | FAIL | Sharpe -0.05, trades/yr 12.0
[0153] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=0d top3 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0153] 2026-08-23 17:17:40 EDT | RESULT | return +384.1% vs B&H +342.7% | maxDD -28.7% vs B&H -34.6% | PASS | Sharpe 0.78, trades/yr 12.0
[0154] 2026-08-23 17:17:40 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top1 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0154] 2026-08-23 17:17:40 EDT | RESULT | return +41.2% vs B&H +37.9% | maxDD -56.6% vs B&H -52.6% | FAIL | Sharpe 0.17, trades/yr 3.9
[0155] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top1 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0155] 2026-08-23 17:17:41 EDT | RESULT | return +404.6% vs B&H +342.7% | maxDD -31.2% vs B&H -34.6% | PASS | Sharpe 0.64, trades/yr 4.1
[0156] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top1 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0156] 2026-08-23 17:17:41 EDT | RESULT | return +41.2% vs B&H +37.9% | maxDD -56.6% vs B&H -52.6% | FAIL | Sharpe 0.17, trades/yr 3.9
[0157] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top1 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0157] 2026-08-23 17:17:41 EDT | RESULT | return +404.6% vs B&H +342.7% | maxDD -31.2% vs B&H -34.6% | PASS | Sharpe 0.64, trades/yr 4.1
[0158] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top2 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0158] 2026-08-23 17:17:41 EDT | RESULT | return +21.0% vs B&H +37.9% | maxDD -48.7% vs B&H -52.6% | FAIL | Sharpe 0.10, trades/yr 6.8
[0159] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top2 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0159] 2026-08-23 17:17:41 EDT | RESULT | return +293.8% vs B&H +342.7% | maxDD -32.5% vs B&H -34.6% | FAIL | Sharpe 0.62, trades/yr 5.5
[0160] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top2 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0160] 2026-08-23 17:17:41 EDT | RESULT | return +8.0% vs B&H +37.9% | maxDD -48.2% vs B&H -52.6% | FAIL | Sharpe 0.05, trades/yr 12.0
[0161] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top2 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0161] 2026-08-23 17:17:41 EDT | RESULT | return +270.6% vs B&H +342.7% | maxDD -32.8% vs B&H -34.6% | FAIL | Sharpe 0.60, trades/yr 12.0
[0162] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top3 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0162] 2026-08-23 17:17:41 EDT | RESULT | return +31.8% vs B&H +37.9% | maxDD -48.6% vs B&H -52.6% | FAIL | Sharpe 0.12, trades/yr 7.3
[0163] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top3 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0163] 2026-08-23 17:17:41 EDT | RESULT | return +313.6% vs B&H +342.7% | maxDD -29.5% vs B&H -34.6% | FAIL | Sharpe 0.68, trades/yr 6.8
[0164] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top3 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0164] 2026-08-23 17:17:41 EDT | RESULT | return +19.9% vs B&H +37.9% | maxDD -46.3% vs B&H -52.6% | FAIL | Sharpe 0.07, trades/yr 12.0
[0165] 2026-08-23 17:17:41 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=189d skip=21d top3 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0165] 2026-08-23 17:17:41 EDT | RESULT | return +305.5% vs B&H +342.7% | maxDD -29.3% vs B&H -34.6% | FAIL | Sharpe 0.68, trades/yr 12.0
[0166] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top1 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0166] 2026-08-23 17:17:42 EDT | RESULT | return +41.8% vs B&H +37.9% | maxDD -54.1% vs B&H -52.6% | FAIL | Sharpe 0.17, trades/yr 3.5
[0167] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top1 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0167] 2026-08-23 17:17:42 EDT | RESULT | return +382.8% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.63, trades/yr 4.1
[0168] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top1 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0168] 2026-08-23 17:17:42 EDT | RESULT | return +41.8% vs B&H +37.9% | maxDD -54.1% vs B&H -52.6% | FAIL | Sharpe 0.17, trades/yr 3.5
[0169] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top1 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0169] 2026-08-23 17:17:42 EDT | RESULT | return +382.8% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.63, trades/yr 4.1
[0170] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top2 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0170] 2026-08-23 17:17:42 EDT | RESULT | return +58.9% vs B&H +37.9% | maxDD -45.1% vs B&H -52.6% | PASS | Sharpe 0.20, trades/yr 6.1
[0171] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top2 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0171] 2026-08-23 17:17:42 EDT | RESULT | return +316.7% vs B&H +342.7% | maxDD -31.3% vs B&H -34.6% | FAIL | Sharpe 0.65, trades/yr 5.9
[0172] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top2 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0172] 2026-08-23 17:17:42 EDT | RESULT | return +43.4% vs B&H +37.9% | maxDD -42.9% vs B&H -52.6% | PASS | Sharpe 0.15, trades/yr 12.0
[0173] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top2 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0173] 2026-08-23 17:17:42 EDT | RESULT | return +278.1% vs B&H +342.7% | maxDD -31.5% vs B&H -34.6% | FAIL | Sharpe 0.62, trades/yr 12.0
[0174] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top3 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0174] 2026-08-23 17:17:42 EDT | RESULT | return +27.4% vs B&H +37.9% | maxDD -44.7% vs B&H -52.6% | FAIL | Sharpe 0.09, trades/yr 8.5
[0175] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top3 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0175] 2026-08-23 17:17:42 EDT | RESULT | return +319.0% vs B&H +342.7% | maxDD -28.3% vs B&H -34.6% | FAIL | Sharpe 0.68, trades/yr 6.5
[0176] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top3 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0176] 2026-08-23 17:17:42 EDT | RESULT | return +3.5% vs B&H +37.9% | maxDD -45.5% vs B&H -52.6% | FAIL | Sharpe -0.01, trades/yr 12.0
[0177] 2026-08-23 17:17:42 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=0d top3 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0177] 2026-08-23 17:17:42 EDT | RESULT | return +288.8% vs B&H +342.7% | maxDD -27.8% vs B&H -34.6% | FAIL | Sharpe 0.66, trades/yr 12.0
[0178] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top1 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0178] 2026-08-23 17:17:43 EDT | RESULT | return +16.1% vs B&H +37.9% | maxDD -56.7% vs B&H -52.6% | FAIL | Sharpe 0.11, trades/yr 3.6
[0179] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top1 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0179] 2026-08-23 17:17:43 EDT | RESULT | return +399.8% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.63, trades/yr 4.1
[0180] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top1 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0180] 2026-08-23 17:17:43 EDT | RESULT | return +16.1% vs B&H +37.9% | maxDD -56.7% vs B&H -52.6% | FAIL | Sharpe 0.11, trades/yr 3.6
[0181] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top1 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0181] 2026-08-23 17:17:43 EDT | RESULT | return +399.8% vs B&H +342.7% | maxDD -30.7% vs B&H -34.6% | PASS | Sharpe 0.63, trades/yr 4.1
[0182] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top2 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0182] 2026-08-23 17:17:43 EDT | RESULT | return +69.5% vs B&H +37.9% | maxDD -45.4% vs B&H -52.6% | PASS | Sharpe 0.23, trades/yr 5.7
[0183] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top2 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0183] 2026-08-23 17:17:43 EDT | RESULT | return +377.4% vs B&H +342.7% | maxDD -32.5% vs B&H -34.6% | PASS | Sharpe 0.69, trades/yr 6.0
[0184] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top2 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0184] 2026-08-23 17:17:43 EDT | RESULT | return +60.0% vs B&H +37.9% | maxDD -44.2% vs B&H -52.6% | PASS | Sharpe 0.20, trades/yr 11.9
[0185] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top2 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0185] 2026-08-23 17:17:43 EDT | RESULT | return +358.0% vs B&H +342.7% | maxDD -32.8% vs B&H -34.6% | PASS | Sharpe 0.68, trades/yr 12.0
[0186] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top3 EW, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0186] 2026-08-23 17:17:43 EDT | RESULT | return +51.2% vs B&H +37.9% | maxDD -48.1% vs B&H -52.6% | PASS | Sharpe 0.18, trades/yr 8.5
[0187] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top3 EW, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0187] 2026-08-23 17:17:43 EDT | RESULT | return +389.9% vs B&H +342.7% | maxDD -29.8% vs B&H -34.6% | PASS | Sharpe 0.74, trades/yr 6.3
[0188] 2026-08-23 17:17:43 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top3 IV, monthly, EW bench | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0188] 2026-08-23 17:17:43 EDT | RESULT | return +31.3% vs B&H +37.9% | maxDD -46.4% vs B&H -52.6% | FAIL | Sharpe 0.11, trades/yr 11.9
[0189] 2026-08-23 17:17:44 EDT | REGISTERED | IDEA-004+066+102 | 9 SPDR sectors | form=252d skip=21d top3 IV, monthly, EW bench | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0189] 2026-08-23 17:17:44 EDT | RESULT | return +361.9% vs B&H +342.7% | maxDD -29.5% vs B&H -34.6% | PASS | Sharpe 0.73, trades/yr 12.0
[0115] 2026-08-23 17:32 EDT | NOTE | IDEA-004 era check (variants 0118-0189): FAILS 2000-2009 outright (+16% vs B&H +38%, maxDD -57% vs -53%). Top-1 concentration = maximum selection risk; train pass judged era-fragile. RECOMMENDATION: KILL.
[0043] 2026-08-23 17:32 EDT | NOTE | IDEA-102 era check: FAILS 2000-2009 (+21% vs B&H +38%). Inv-vol tweak adds nothing over EW (train margin +2pp/13yr = noise) and is an extra degree of freedom. RECOMMENDATION: KILL.
[0042] 2026-08-23 17:32 EDT | NOTE | IDEA-066 era check: PASSES both eras, but 2000-2009 margin is ~1pp total return over a decade (Sharpe 0.14) - statistically indistinguishable from noise. Setting-ranking across eras: Spearman rho -0.18 (Sharpe) => parameter ordering is noise; family edge is regime-level, not setting-level. RECOMMENDATION: KEEP (sole family representative, low conviction) for eventual locked-TEST scoring.
[0190] 2026-08-23 17:26:02 EDT | REGISTERED | IDEA-103 | QQQ/GLD | QQQ while close>SMA200 else GLD; daily signal | 2010-01-01..2022-12-31 | pending
[0190] 2026-08-23 17:26:02 EDT | RESULT | return +330.4% vs B&H +248.8% | maxDD -29.5% vs B&H -24.0% | FAIL | Sharpe 0.69, trades/yr 6.9
[0191] 2026-08-23 17:26:02 EDT | REGISTERED | IDEA-104 | 20-ETF universe | monthly top-5 by close/252d-high; cash when SPY<SMA200 | ADAPT: 20-ETF universe substitutes for published '50 ETFs' | 2010-01-01..2022-12-31 | pending
[0191] 2026-08-23 17:26:02 EDT | RESULT | return +113.6% vs B&H +216.3% | maxDD -19.7% vs B&H -27.9% | FAIL | Sharpe 0.65, trades/yr 10.6
[0192] 2026-08-23 17:26:02 EDT | REGISTERED | IDEA-105 | SPY | IBS<=0.1 & >SMA200 entry; exit IBS>=0.9 or 3 days | 2010-01-01..2022-12-31 | pending
[0192] 2026-08-23 17:26:02 EDT | RESULT | return +58.1% vs B&H +333.8% | maxDD -15.0% vs B&H -32.0% | FAIL | Sharpe 0.50, trades/yr 28.1
[0193] 2026-08-23 17:26:02 EDT | REGISTERED | IDEA-107 | QQQ | w=20%/realized20, cap 2.0, daily; financing on leverage | 2010-01-01..2022-12-31 | pending
[0193] 2026-08-23 17:26:02 EDT | RESULT | return +815.2% vs B&H +542.9% | maxDD -30.3% vs B&H -36.7% | PASS | Sharpe 0.85, trades/yr 213.5 | 2x: +721.9% 3x: +638.0%
[0194] 2026-08-23 17:26:02 EDT | REGISTERED | IDEA-108 | blend of IDEA-066+IDEA-107 | inverse-vol (63d) monthly, no tuning | 2010-01-01..2022-12-31 | pending
[0194] 2026-08-23 17:26:02 EDT | RESULT | CAGR +15.36%, Sharpe 0.87, maxDD -25.1% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | components: IDEA-066+IDEA-107 | reallocation costs between strategies not modeled
[0195] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=15% cap=1.0x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0195] 2026-08-23 17:28:44 EDT | RESULT | return +22.2% vs B&H -50.5% | maxDD -42.9% vs B&H -83.1% | PASS | Sharpe 0.04, trades/yr 195.5
[0196] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=15% cap=1.0x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0196] 2026-08-23 17:28:44 EDT | RESULT | return +394.9% vs B&H +542.9% | maxDD -22.4% vs B&H -36.7% | FAIL | Sharpe 0.87, trades/yr 129.5
[0197] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=15% cap=1.5x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0197] 2026-08-23 17:28:44 EDT | RESULT | return +16.4% vs B&H -50.5% | maxDD -42.9% vs B&H -83.1% | PASS | Sharpe 0.01, trades/yr 248.9
[0198] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=15% cap=1.5x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0198] 2026-08-23 17:28:44 EDT | RESULT | return +487.9% vs B&H +542.9% | maxDD -23.2% vs B&H -36.7% | FAIL | Sharpe 0.86, trades/yr 213.5
[0199] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=15% cap=2.0x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0199] 2026-08-23 17:28:44 EDT | RESULT | return +15.7% vs B&H -50.5% | maxDD -42.9% vs B&H -83.1% | PASS | Sharpe 0.01, trades/yr 251.9
[0200] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=15% cap=2.0x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0200] 2026-08-23 17:28:44 EDT | RESULT | return +505.1% vs B&H +542.9% | maxDD -23.2% vs B&H -36.7% | FAIL | Sharpe 0.85, trades/yr 241.0
[0201] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=20% cap=1.0x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0201] 2026-08-23 17:28:44 EDT | RESULT | return +10.0% vs B&H -50.5% | maxDD -54.8% vs B&H -83.1% | PASS | Sharpe 0.01, trades/yr 152.0
[0202] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=20% cap=1.0x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0202] 2026-08-23 17:28:44 EDT | RESULT | return +480.0% vs B&H +542.9% | maxDD -28.7% vs B&H -36.7% | FAIL | Sharpe 0.85, trades/yr 77.2
[0203] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=20% cap=1.5x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0203] 2026-08-23 17:28:44 EDT | RESULT | return +9.4% vs B&H -50.5% | maxDD -54.8% vs B&H -83.1% | PASS | Sharpe 0.02, trades/yr 213.6
[0204] 2026-08-23 17:28:44 EDT | REGISTERED | IDEA-107 | QQQ | target=20% cap=1.5x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0204] 2026-08-23 17:28:44 EDT | RESULT | return +693.9% vs B&H +542.9% | maxDD -29.6% vs B&H -36.7% | PASS | Sharpe 0.85, trades/yr 155.8
[0205] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=20% cap=2.0x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0205] 2026-08-23 17:28:45 EDT | RESULT | return +3.8% vs B&H -50.5% | maxDD -54.8% vs B&H -83.1% | PASS | Sharpe 0.00, trades/yr 248.9
[0206] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=20% cap=2.0x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0206] 2026-08-23 17:28:45 EDT | RESULT | return +815.2% vs B&H +542.9% | maxDD -30.3% vs B&H -36.7% | PASS | Sharpe 0.85, trades/yr 213.5
[0207] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=25% cap=1.0x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0207] 2026-08-23 17:28:45 EDT | RESULT | return -4.9% vs B&H -50.5% | maxDD -64.4% vs B&H -83.1% | PASS | Sharpe -0.03, trades/yr 110.9
[0208] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=25% cap=1.0x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0208] 2026-08-23 17:28:45 EDT | RESULT | return +494.9% vs B&H +542.9% | maxDD -33.2% vs B&H -36.7% | FAIL | Sharpe 0.80, trades/yr 51.5
[0209] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=25% cap=1.5x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0209] 2026-08-23 17:28:45 EDT | RESULT | return -1.0% vs B&H -50.5% | maxDD -64.5% vs B&H -83.1% | PASS | Sharpe 0.02, trades/yr 178.8
[0210] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=25% cap=1.5x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0210] 2026-08-23 17:28:45 EDT | RESULT | return +875.2% vs B&H +542.9% | maxDD -35.6% vs B&H -36.7% | PASS | Sharpe 0.84, trades/yr 109.9
[0211] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=25% cap=2.0x realized20 | 2000-01-01..2009-12-31 | pending (neighborhood/era check)
[0211] 2026-08-23 17:28:45 EDT | RESULT | return -5.8% vs B&H -50.5% | maxDD -64.5% vs B&H -83.1% | PASS | Sharpe 0.01, trades/yr 226.6
[0212] 2026-08-23 17:28:45 EDT | REGISTERED | IDEA-107 | QQQ | target=25% cap=2.0x realized20 | 2010-01-01..2022-12-31 | pending (neighborhood/era check)
[0212] 2026-08-23 17:28:45 EDT | RESULT | return +1097.0% vs B&H +542.9% | maxDD -36.4% vs B&H -36.7% | PASS | Sharpe 0.84, trades/yr 168.0
[0193] 2026-08-23 17:34 EDT | NOTE | IDEA-107 era check (variants 0195-0203): all 9 settings "PASS" 2000-2009 ONLY because QQQ B&H was -50.5% with -83.1% maxDD (dot-com) - a trivially low bar. Absolute 2000s performance was ~0% return with -43% to -64% drawdowns, i.e. not tradeable on its own merits. Return-rank across eras Spearman rho -0.77 (NEGATIVE): higher vol targets win in the 2010s bull and lose in the 2000s bear, so the setting surface is a leverage/regime bet, not a stable edge. Vol-matched check (same realized vol as strategy): static leverage Sharpe 0.77/DD -39.7% vs vol-target 0.85/-30.3%, so the vol-scaling mechanism itself is real. Survives 3x costs (CAGR +16.7%). Runs 1.33x average leverage, 17% of time at the 2x cap. RECOMMENDATION: KEEP, low conviction, leverage-aware.
[0192] 2026-08-23 17:34 EDT | NOTE | IDEA-105 train result (Sharpe 0.50, maxDD -15.0%, CAGR +3.6%) is far from the source card's claimed Sharpe 2.43 / maxDD -3.5% / CAGR +14.0%. Card figures are a different (TEST-era) period from an external run and are not evidence here; discrepancy of this size is itself a reason for suspicion of the source rather than of our run.
[0117] 2026-08-23 17:37 EDT | NOTE | AUDIT: this ID carries TWO REGISTERED lines (17:11:50 and 17:12:32). The first run was killed by the automated lookahead check before producing a RESULT (calendar flag shifted after reindex); the 17:12:32 registration is the re-run that produced the single RESULT line. Both registrations are retained per the append-only rule. Ledger arithmetic: 214 REGISTERED lines, 212 distinct variant IDs, 0 gaps, 0 registrations without a RESULT.
[0212] 2026-08-23 17:37 EDT | NOTE | CORRECTION to the note filed against [0193]: the IDEA-107 era/neighborhood check occupies variants 0195-0212 (18 = 3 targets x 3 caps x 2 eras), not "0195-0203" as that note stated. Findings in that note are unchanged.
[0213] 2026-08-23 17:32:23 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.50%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0213] 2026-08-23 17:32:45 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.50%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0213] 2026-08-23 17:32:45 EDT | RESULT | CAGR +3.00%, Sharpe 0.11, maxDD -23.1% | vs SPY CAGR +0.07%/DD -55.4%, QQQ CAGR -2.29%/DD -70.7% | PASS | mean gross 0.57x, max 0.96x | 2x costs CAGR +2.89% 3x +2.78%
[0214] 2026-08-23 17:32:45 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.50%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2010-01-01..2022-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0214] 2026-08-23 17:32:45 EDT | RESULT | CAGR +8.18%, Sharpe 0.75, maxDD -12.9% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | FAIL | mean gross 0.73x, max 1.00x | 2x costs CAGR +8.03% 3x +7.88%
[0215] 2026-08-23 17:32:46 EDT | REGISTERED | IDEA-110 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.50%/trade, exit=2xATR20, cap25%/6pos/grossSPYvol lev<=3x, financing on | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0215] 2026-08-23 17:32:46 EDT | RESULT | CAGR -0.55%, Sharpe -0.05, maxDD -50.6% | vs SPY CAGR +0.07%/DD -55.4%, QQQ CAGR -2.29%/DD -70.7% | FAIL | mean gross 0.95x, max 1.67x | 2x costs CAGR -0.87% 3x -1.19%
[0216] 2026-08-23 17:32:46 EDT | REGISTERED | IDEA-110 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.50%/trade, exit=2xATR20, cap25%/6pos/grossSPYvol lev<=3x, financing on | 2010-01-01..2022-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0216] 2026-08-23 17:32:46 EDT | RESULT | CAGR +12.30%, Sharpe 0.78, maxDD -23.1% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | PASS | mean gross 1.00x, max 2.15x | 2x costs CAGR +11.86% 3x +11.43%
[0217] 2026-08-23 17:32:46 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.75%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0217] 2026-08-23 17:32:46 EDT | RESULT | CAGR +2.87%, Sharpe 0.11, maxDD -33.3% | vs SPY CAGR +0.07%/DD -55.4%, QQQ CAGR -2.29%/DD -70.7% | PASS | mean gross 0.78x, max 1.00x | 2x costs CAGR +2.75% 3x +2.62%
[0218] 2026-08-23 17:32:47 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.75%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2010-01-01..2022-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0218] 2026-08-23 17:32:47 EDT | RESULT | CAGR +10.94%, Sharpe 0.80, maxDD -15.6% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | FAIL | mean gross 0.90x, max 1.00x | 2x costs CAGR +10.79% 3x +10.65%
[0219] 2026-08-23 17:32:47 EDT | REGISTERED | IDEA-110 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.75%/trade, exit=2xATR20, cap25%/6pos/grossSPYvol lev<=3x, financing on | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0219] 2026-08-23 17:32:47 EDT | RESULT | CAGR -1.31%, Sharpe -0.06, maxDD -57.5% | vs SPY CAGR +0.07%/DD -55.4%, QQQ CAGR -2.29%/DD -70.7% | FAIL | mean gross 0.99x, max 1.87x | 2x costs CAGR -1.68% 3x -2.05%
[0220] 2026-08-23 17:32:47 EDT | REGISTERED | IDEA-110 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=0.75%/trade, exit=2xATR20, cap25%/6pos/grossSPYvol lev<=3x, financing on | 2010-01-01..2022-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0220] 2026-08-23 17:32:47 EDT | RESULT | CAGR +13.36%, Sharpe 0.82, maxDD -22.0% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | PASS | mean gross 0.99x, max 2.25x | 2x costs CAGR +12.95% 3x +12.55%
[0221] 2026-08-23 17:32:48 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=1.00%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0221] 2026-08-23 17:32:48 EDT | RESULT | CAGR +2.33%, Sharpe 0.08, maxDD -39.6% | vs SPY CAGR +0.07%/DD -55.4%, QQQ CAGR -2.29%/DD -70.7% | PASS | mean gross 0.87x, max 1.00x | 2x costs CAGR +2.20% 3x +2.08%
[0222] 2026-08-23 17:32:48 EDT | REGISTERED | IDEA-109 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=1.00%/trade, exit=2xATR20, cap25%/6pos/gross100%, 20% book vol | 2010-01-01..2022-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0222] 2026-08-23 17:32:48 EDT | RESULT | CAGR +11.81%, Sharpe 0.79, maxDD -18.3% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | FAIL | mean gross 0.95x, max 1.00x | 2x costs CAGR +11.66% 3x +11.52%
[0223] 2026-08-23 17:32:48 EDT | REGISTERED | IDEA-110 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=1.00%/trade, exit=2xATR20, cap25%/6pos/grossSPYvol lev<=3x, financing on | 2001-01-01..2009-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0223] 2026-08-23 17:32:48 EDT | RESULT | CAGR -1.59%, Sharpe -0.06, maxDD -59.5% | vs SPY CAGR +0.07%/DD -55.4%, QQQ CAGR -2.29%/DD -70.7% | FAIL | mean gross 0.98x, max 1.90x | 2x costs CAGR -1.94% 3x -2.29%
[0224] 2026-08-23 17:32:49 EDT | REGISTERED | IDEA-110 | book: IDEA-066 sectors + IDEA-107 QQQ | risk=1.00%/trade, exit=2xATR20, cap25%/6pos/grossSPYvol lev<=3x, financing on | 2010-01-01..2022-12-31 | pending | ADAPT: 2xATR20 exit-distance proxy (no published stop in either component)
[0224] 2026-08-23 17:32:49 EDT | RESULT | CAGR +13.14%, Sharpe 0.80, maxDD -23.3% | vs SPY CAGR +11.95%/DD -32.0%, QQQ CAGR +15.40%/DD -36.7% | PASS | mean gross 0.98x, max 2.09x | 2x costs CAGR +12.78% 3x +12.42%
[0224] 2026-08-23 17:42 EDT | NOTE | IDEA-109/110 risk-layer conclusions (variants 0213-0224). Leverage is Sharpe-neutral: 2010-2022 at risk=0.75% it moved Sharpe 0.80 -> 0.82 while CAGR went +10.94% -> +13.36% and maxDD -15.6% -> -22.0%; i.e. it scales the existing edge, it does not create one. In 2001-2009 it multiplied a marginal book into a losing one: CAGR +2.87% -> -1.31%, maxDD -33.3% -> -57.5%. Loss amplification exceeds gain amplification (2008: -22% -> -39%, ratio 1.77x; 2003: +25% -> +31%, ratio 1.24x) because the 20-day trailing vol estimator levers UP into low-vol calm and is still levered when vol gaps. Financing drag is small (~0.2-0.3%/yr at mean borrowed 0.08x) and is NOT the reason leverage hurt. TEST WINDOW NOT TOUCHED for any of these variants; user has not said UNLOCK.
[0225] 2026-08-23 17:58 EDT | REGISTERED | IDEA-066 | 9 SPDR sectors | 6m return rank, top 3 EW, monthly; month-end flags now CALENDAR-derived (next weekday in a new month) instead of data-index-derived | 2010-01-01..2022-12-31 | pending (re-registration: the calendar basis changed, so this is a new variant rather than an edit of [0042])
[0225] 2026-08-23 17:58 EDT | RESULT | return +391.9% vs B&H +342.7% | maxDD -29.0% vs B&H -34.6% | PASS | Sharpe 0.77, trades/yr 7.6
[0225] 2026-08-23 17:58 EDT | NOTE | Why the change: the original data-index month-end rule marked the LAST AVAILABLE BAR as a month-end. Under truncation that silently altered past decisions (caught by the automated lookahead check), and on live bars a research-window calendar produced all-False, i.e. "never rebalance" - the live loop computed zero sector weights on its first run because of exactly this. The calendar-derived rule is truncation-invariant and runs identically on research and live data. Effect on results is small (+391.9% vs [0042]'s +382.9%, identical Sharpe 0.77 and maxDD -29.0%), which is itself evidence the edge does not hinge on the holiday-month edge cases where the two definitions disagree. [0042] stands as recorded; this supersedes it for anything deployed.
