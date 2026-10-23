"""Implied volatility by Brent's method with no-arbitrage bound checks."""
import numpy as np
from scipy.optimize import brentq

from .bs import price

LO, HI = 1e-4, 5.0


def implied_vol(p, S, K, T, r, q, kind="call") -> float:
    """Return NaN when the price is outside the BS no-arbitrage bounds."""
    dfq, dfr = np.exp(-q * T), np.exp(-r * T)
    intrinsic = max(S * dfq - K * dfr, 0) if kind == "call" else max(K * dfr - S * dfq, 0)
    upper = S * dfq if kind == "call" else K * dfr
    if not (intrinsic < p < upper):
        return float("nan")
    f = lambda v: price(S, K, T, r, q, v, kind) - p  # noqa: E731
    if f(LO) * f(HI) > 0:
        return float("nan")
    return float(brentq(f, LO, HI, xtol=1e-10))
