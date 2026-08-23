"""Live-trading configuration, paper-only enforcement, and HARD LIMITS.

Two distinct layers of protection, deliberately kept apart:

  * HARD LIMITS (this file, in code)  - structural caps that no config file,
    flag, or runtime argument can relax. Defence in depth: even if
    HALT_RULES.yaml were edited to something reckless, these still bind.
  * HALT RULES (../HALT_RULES.yaml)   - performance thresholds the owner
    tunes deliberately between sessions.

REAL MONEY IS OFF. `REAL_MONEY_ENABLED = False` and four independent checks
must all agree the account is paper before a single order is submitted.
Flipping this is a deliberate act by the owner, not a code change an agent
should ever make on its own.
"""

import os
from pathlib import Path

from dotenv import dotenv_values

# ---------------------------------------------------------------------------
# REAL MONEY GATE
# ---------------------------------------------------------------------------
REAL_MONEY_ENABLED = False          # Jainithin flips this, nobody else.
PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"

# ---------------------------------------------------------------------------
# HARD LIMITS (in code, not configurable)
# ---------------------------------------------------------------------------
MAX_POSITION_PCT = 0.25       # no single symbol above 25% of equity
MAX_OPEN_POSITIONS = 6        # no more than 6 symbols held at once
MAX_GROSS_EXPOSURE = 1.00     # unlevered book: gross <= 100% of equity
MAX_ORDER_PCT = 0.25          # no single order larger than 25% of equity
MAX_ORDERS_PER_DAY = 20       # runaway-loop circuit breaker
MIN_ORDER_NOTIONAL = 25.0     # skip dust

# Tier-2 emergency triggers ("anything looks wrong" -> flatten + halt)
MAX_DATA_STALENESS_DAYS = 4   # bars older than this = we are flying blind
MAX_CONSECUTIVE_API_ERRORS = 3
UNEXPECTED_SYMBOL_IS_FATAL = True   # holding something the book never chose

# ---------------------------------------------------------------------------
# The deployed book
# ---------------------------------------------------------------------------
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
TRADED_UNIVERSE = SECTORS + ["QQQ"]        # what the book may hold
REFERENCE_SYMBOLS = ["SPY"]                # data only, never traded
RISK_PCT_PER_TRADE = 0.0075                # IDEA-109 @0.75%, variant [0217]
WARMUP_TRADING_DAYS = 260                  # enough for 126d formation + ATR20

LIVE_DIR = Path(__file__).resolve().parent
MARKET_CACHE = LIVE_DIR / "market_cache"   # live bars; research NEVER reads this
JOURNAL_PATH = LIVE_DIR / "JOURNAL.jsonl"
LIVE_RETURNS_PATH = LIVE_DIR / "live_returns.csv"


class NotPaperAccount(RuntimeError):
    """Raised when anything suggests this is not a paper account."""


def load_credentials(env_path=None):
    """Read Alpaca creds. Never logs or returns the secret in cleartext."""
    # LIVE_DIR = <project>/research/live  ->  parents[1] = <project>
    env_path = env_path or (LIVE_DIR.parents[1] / "regime-trader" / ".env")
    vals = {**dotenv_values(env_path), **{k: v for k, v in os.environ.items()
                                          if k.startswith("ALPACA_")}}
    key = vals.get("ALPACA_API_KEY", "")
    secret = vals.get("ALPACA_SECRET_KEY", "")
    paper_flag = str(vals.get("ALPACA_PAPER", "")).strip().lower() in ("true", "1", "yes")
    if not key or not secret:
        raise NotPaperAccount("Alpaca credentials missing")
    return key, secret, paper_flag


def assert_paper(key: str, paper_flag: bool, base_url: str, account=None):
    """Four independent checks. ALL must agree this is paper.

    Any single one failing aborts. This runs before every order submission,
    not just at startup, so a mid-session credential swap cannot slip past.
    """
    if REAL_MONEY_ENABLED:
        raise NotPaperAccount(
            "REAL_MONEY_ENABLED is True but the owner has not authorised live "
            "trading in this session. Refusing to trade.")
    if not key.startswith("PK"):
        raise NotPaperAccount(
            f"API key prefix {key[:2]!r} is not a paper key (expected 'PK'). "
            f"Refusing to trade.")
    if not paper_flag:
        raise NotPaperAccount("ALPACA_PAPER is not true. Refusing to trade.")
    if base_url != PAPER_BASE_URL:
        raise NotPaperAccount(
            f"base_url {base_url!r} is not the paper endpoint. Refusing to trade.")
    if account is not None:
        # Alpaca marks paper accounts; a live account number here is fatal.
        if getattr(account, "status", None) is None:
            raise NotPaperAccount("account object has no status; cannot verify paper")
        pattern = str(getattr(account, "account_number", ""))
        if pattern and not pattern.upper().startswith("PA"):
            raise NotPaperAccount(
                f"account_number {pattern!r} does not look like a paper account "
                f"(expected 'PA...'). Refusing to trade.")
    return True
