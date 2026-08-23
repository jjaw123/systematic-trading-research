"""Hard-coded, non-negotiable rules of the research protocol.

These constants are the protocol. They are not configuration: no code path may
override them, and no backtest may run outside them.
"""

# ---- Data split -------------------------------------------------------------
# TRAIN evaluation window: performance is scored on 2010-01-01..2022-12-31.
# Data before 2010 may be used only for indicator warmup (it is still causal).
# TEST (2023-01-01 onward) is LOCKED: it must not be loaded, read, or touched
# by any code until the user says the exact word UNLOCK.
TRAIN_EVAL_START = "2010-01-01"
TRAIN_END = "2022-12-31"
TEST_START = "2023-01-01"
LOCKED_DIR_NAME = "test_locked"

# ---- Costs (always on; there is no zero-cost mode) --------------------------
ETF_BPS_PER_SIDE = 2.0            # ETFs and liquid single-name equities
FINANCING_SPREAD_BPS = 150.0      # paid over T-bill on borrowed (gross > 1x)
SHORT_BORROW_BPS = 50.0           # annualized borrow fee on short notional
# Futures: real round-trip cost = slippage (ticks) + commission, both sides,
# converted to bps of notional at the prevailing price. Specs must be
# registered here before any futures asset is backtested.
FUTURES_SPECS = {
    # root: dict(tick_value=$ per tick per contract, slippage_ticks per side,
    #            commission=$ per side per contract, multiplier=$ per point)
    "GC": dict(tick_value=10.0, slippage_ticks=1.0, commission=2.50, multiplier=100.0),
    "ES": dict(tick_value=12.50, slippage_ticks=0.5, commission=2.50, multiplier=50.0),
}

# Cost stress: any strategy trading more than weekly must also be reported at
# these multiples of all trading-cost assumptions.
WEEKLY_TRADES_PER_YEAR = 52.0
COST_STRESS_MULTIPLIERS = (2.0, 3.0)

# ---- Absurdity gate ---------------------------------------------------------
# If a backtest prints an absurd number it is treated as a bug: the result is
# flagged, the PASS/FAIL verdict is withheld, and leakage must be hunted before
# the result is shown or recorded.
ABSURD_SHARPE = 3.0               # annualized, net of costs
ABSURD_CAGR = 0.50                # 50%/yr on daily bars = presumed leakage
ABSURD_HIT_RATE = 0.90            # >90% of active days positive
ABSURD_SHALLOW_DD = 0.03          # CAGR > 15% with max drawdown < 3%
ABSURD_SHALLOW_DD_CAGR = 0.15

# ---- Numerics ---------------------------------------------------------------
TRADING_DAYS_PER_YEAR = 252
WEIGHT_TOLERANCE = 1e-9
LOOKAHEAD_CHECK_DATES = 12        # truncation points per automated check
LOOKAHEAD_SEED = 20260823
