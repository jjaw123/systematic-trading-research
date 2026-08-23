# regime-trader

HMM-based market regime detection driving volatility-conditioned portfolio
allocation, with walk-forward backtesting, stress testing, and paper trading
via Alpaca.

**Design philosophy**: the HMM is a *volatility classifier*, not a direction
predictor. Calm markets trend up most of the time and the worst drawdowns
cluster in volatility spikes — so the strategy is fully invested (with
modest leverage) when calm, reduced when turbulent, and always long-only.
Regime *labels* (bull/bear/crash/…) are cosmetic, sorted by return;
strategy assignment sorts independently by each regime's volatility.

## Architecture

1. **Data** (`core/data/`) — Alpaca historical + streaming bars; causal
   feature engineering (returns, realized vol, ADX, RSI, ATR — every value
   at bar *t* uses only bars ≤ *t*).
2. **Regime detection** (`core/hmm_engine.py`) — Gaussian HMM with BIC
   state-count selection (3–7 states, multi-restart) and **forward-algorithm
   inference only** (never Viterbi — it smooths with future data). Regime
   changes confirm after 3 persistent bars; flicker forces uncertainty mode.
3. **Strategy** (`core/regime_strategies.py`) — regimes map to
   Low/Mid/HighVol strategies by volatility rank: 95% @ 1.25x when calm,
   trend-gated 95%/60% mid-vol, 60% defensive (never short) when turbulent.
   Uncertainty halves sizes.
4. **Risk** (`core/risk_manager.py`) — independent veto layer: 1% risk
   sizing, position/exposure/sector caps, gap-risk overnight cap, 60-day
   correlation checks, duplicate/spread/stop-required gates, and P&L-based
   circuit breakers (daily 2%/3%, weekly 5%/7%, 10% peak stop that writes
   `trading_halted.lock` — delete it to resume).
5. **Execution** (`core/broker/`) — alpaca-py wrapper with retry/backoff and
   a typed live-mode confirmation; limit-first orders (±0.1%, 30s timeout,
   market chase), bracket orders, tighten-only stops; fill-stream position
   tracking reconciled with the broker.
6. **Live loop** (`core/live_engine.py`) — startup/recovery, per-cycle
   pipeline, trailing stops, breaker enforcement, weekly retraining, state
   snapshot; SIGINT/SIGTERM shuts down without closing positions.
7. **Monitoring** (`monitoring/`) — structured JSON logs (main/trades/
   regime/alerts, rotating), sectioned rich dashboard with color-coded risk
   bars, a Streamlit web control room (`theme.py` tokens + `ui.py` components
   + `history.py` rolling snapshot log), and rate-limited alerts
   (console/log/email/webhook).
8. **Backtesting** (`backtest/`) — allocation-based walk-forward (252/126
   IS/OOS, refit per fold, next-bar-open fills with slippage), performance
   analytics with regime/confidence breakdowns and benchmarks, and
   crash/gap/misclassification stress suites.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # add Alpaca keys (paper account)
```

`.env`, `config/credentials.yaml`, models, logs, and runtime state are all
gitignored — never commit secrets.

## Usage

```bash
python main.py                       # live loop (paper trading)
python main.py --dry-run             # full pipeline, no orders
python main.py --train-only          # train the HMM and exit
python main.py --dashboard           # attach a terminal dashboard

streamlit run monitoring/streamlit_app.py   # web control room :8501

python main.py --backtest --symbols SPY --start 2019-01-01 --compare
python main.py --backtest --stress-test --sims 100
python main.py --backtest --symbols DEMO --synthetic   # demo without data
```

The web dashboard has five views (Overview / Positions / Signals / Risk /
System) and reads three optional sources: the Alpaca API, `state_snapshot.json`
(current engine state) and `state_history.jsonl` (the rolling per-cycle log
behind the equity curve and regime ribbon). It runs standalone — with no
engine and no credentials every panel degrades to an empty state explaining
what to start.

Backtests read `data/<SYMBOL>.csv` (date,open,high,low,close,volume) or
generate demo bars with `--synthetic`. All parameters live in
`config/settings.yaml`. Paper trading is the default; live trading requires
`ALPACA_PAPER=false` **and** typing the confirmation phrase at startup.

## Tests

```bash
pytest tests/
```

~130 tests cover the full stack. The load-bearing ones:

- `test_look_ahead.py` — the causality suite: features, filtered HMM
  inference, and the *entire backtest* must be bit-identical when future
  data is appended.
- `test_integration.py` — end-to-end chain (data → HMM → strategy → risk →
  orders with a full audit trail), risk stress (extreme signals capped,
  rapid-fire blocked, no-stop rejected), and crash-recovery (restart
  reconciles with the broker and never double-enters). A real paper-API
  bracket lifecycle test runs automatically when `.env` has credentials.
- `test_risk.py` / `test_orders.py` / `test_live.py` / `test_monitoring.py`
  / `test_backtest.py` / `test_strategies.py` — per-layer suites.

## Safety model

Defense in depth, each layer independent of the ones above it:

- Strategy uncertainty mode (low confidence / flicker) halves sizes.
- The risk manager can veto or resize any signal; every position must have
  a stop; leverage is forced to 1.0x under any stress condition.
- Circuit breakers watch actual P&L only — a wrong regime model cannot
  bypass them (verified by the regime-shuffle stress test).
- The 10% peak-drawdown stop requires manual human intervention (deleting
  `trading_halted.lock`) to resume.

## Disclaimer

For research and paper trading. Nothing here is financial advice; live
trading is at your own risk.
