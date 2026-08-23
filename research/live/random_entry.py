"""Matched random-entry benchmark: what would dart-throwing have produced?

For a rolling window we build a null distribution of strategies that are
matched to the live book on time-in-market and number of position switches,
but whose entry timing is random, applied to the SAME realized market
returns. Beating the market is not the bar; beating this is.
"""

import numpy as np


def _random_path(n, days_in, switches, rng):
    """A 0/1 exposure path of length n with `days_in` invested days spread
    over roughly `switches` position changes, placed at random."""
    if days_in <= 0:
        return np.zeros(n)
    if days_in >= n:
        return np.ones(n)
    blocks = max(1, int(round(switches / 2)))          # switches = in + out
    blocks = min(blocks, days_in, n - days_in)
    # random block lengths summing to days_in
    cuts = np.sort(rng.choice(np.arange(1, days_in), size=blocks - 1, replace=False)) \
        if blocks > 1 else np.array([], dtype=int)
    lengths = np.diff(np.concatenate([[0], cuts, [days_in]]))
    # random gap lengths summing to n - days_in
    gap_total = n - days_in
    gcuts = np.sort(rng.choice(np.arange(1, gap_total), size=blocks - 1, replace=False)) \
        if blocks > 1 and gap_total > blocks else np.array([], dtype=int)
    gaps = np.diff(np.concatenate([[0], gcuts, [gap_total]]))
    path = np.zeros(n)
    pos = 0
    order = rng.permutation(blocks)
    for i in order:
        pos += gaps[i]
        path[pos:pos + lengths[i]] = 1.0
        pos += lengths[i]
    return path[:n]


def null_distribution(market_returns, days_in, switches, exposure,
                      simulations, rng):
    """Distribution of total returns from matched random-entry paths.

    market_returns: realized returns of the traded market over the window
    days_in:        invested days the live book actually had
    switches:       position changes the live book actually made
    exposure:       average gross exposure when invested (scales the paths)
    """
    n = len(market_returns)
    out = np.empty(simulations)
    for i in range(simulations):
        path = _random_path(n, days_in, switches, rng)
        out[i] = np.prod(1.0 + path * exposure * market_returns) - 1.0
    return out


def percentile_of(value, distribution):
    """Where the live result sits inside the null distribution, 0-100."""
    return float((distribution < value).mean() * 100.0)
