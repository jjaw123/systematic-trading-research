"""Cost model. Costs are always on — there is no way to run without them.

Trading costs:  ETFs/equities pay ETF_BPS_PER_SIDE per side on traded notional.
                Futures pay real round-trip costs (slippage ticks + commission)
                converted to bps of notional at the prevailing price.
Financing:      gross exposure above 1x pays (T-bill + FINANCING_SPREAD_BPS)
                on the borrowed fraction, daily.
Short borrow:   short notional pays SHORT_BORROW_BPS annualized, daily.
Idle cash:      fraction of equity not deployed earns the T-bill rate.
"""

import pandas as pd

from .rules import (
    ETF_BPS_PER_SIDE,
    FINANCING_SPREAD_BPS,
    FUTURES_SPECS,
    SHORT_BORROW_BPS,
    TRADING_DAYS_PER_YEAR,
)


def trade_cost_rate(asset_class: str, price: float | None = None,
                    futures_root: str | None = None) -> float:
    """Cost per side as a fraction of traded notional (before stress multiplier)."""
    if asset_class in ("etf", "equity"):
        return ETF_BPS_PER_SIDE / 1e4
    if asset_class == "futures":
        if futures_root not in FUTURES_SPECS:
            raise ValueError(
                f"Futures root {futures_root!r} has no cost spec in rules.FUTURES_SPECS; "
                f"register real round-trip costs before backtesting it."
            )
        if price is None or price <= 0:
            raise ValueError("Futures cost conversion needs the prevailing price.")
        s = FUTURES_SPECS[futures_root]
        notional = price * s["multiplier"]
        per_side_dollars = s["tick_value"] * s["slippage_ticks"] + s["commission"]
        return per_side_dollars / notional
    raise ValueError(f"Unknown asset class: {asset_class!r}")


def daily_carry(gross: pd.Series, short_notional: pd.Series,
                rf_daily: pd.Series, cost_multiplier: float = 1.0) -> pd.Series:
    """Net daily carry: idle-cash yield minus financing minus short borrow.

    All series inputs are aligned; gross/short are fractions of equity. The
    stress multiplier scales the cost spreads (not the T-bill base rate, and
    not the cash yield earned).
    """
    idle_cash = (1.0 - gross).clip(lower=0.0)
    borrowed = (gross - 1.0).clip(lower=0.0)
    spread = FINANCING_SPREAD_BPS * cost_multiplier / 1e4 / TRADING_DAYS_PER_YEAR
    borrow_rate = SHORT_BORROW_BPS * cost_multiplier / 1e4 / TRADING_DAYS_PER_YEAR
    return (idle_cash * rf_daily
            - borrowed * (rf_daily + spread)
            - short_notional * borrow_rate)
