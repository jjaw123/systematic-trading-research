"""All catalog entries, in registration order."""

from strategies import breakout, meanrev, portfolio, trend


def all_entries():
    return (trend.entries() + meanrev.entries() + breakout.entries()
            + portfolio.entries())
