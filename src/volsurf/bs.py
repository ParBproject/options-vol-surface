"""Black-Scholes-Merton with continuous dividend yield q."""
import numpy as np
from scipy.stats import norm


def _d1d2(S, K, T, r, q, vol):
    d1 = (np.log(S / K) + (r - q + 0.5 * vol**2) * T) / (vol * np.sqrt(T))
    return d1, d1 - vol * np.sqrt(T)


def price(S, K, T, r, q, vol, kind="call"):
    d1, d2 = _d1d2(S, K, T, r, q, vol)
    dfq, dfr = np.exp(-q * T), np.exp(-r * T)
    if kind == "call":
        return S * dfq * norm.cdf(d1) - K * dfr * norm.cdf(d2)
    return K * dfr * norm.cdf(-d2) - S * dfq * norm.cdf(-d1)


def greeks(S, K, T, r, q, vol, kind="call") -> dict:
    """Delta, gamma, vega (per 1.00 vol), theta (per year), rho (per 1.00 rate)."""
    d1, d2 = _d1d2(S, K, T, r, q, vol)
    dfq, dfr = np.exp(-q * T), np.exp(-r * T)
    pdf = norm.pdf(d1)
    gamma = dfq * pdf / (S * vol * np.sqrt(T))
    vega = S * dfq * pdf * np.sqrt(T)
    common = -S * dfq * pdf * vol / (2 * np.sqrt(T))
    if kind == "call":
        delta = dfq * norm.cdf(d1)
        theta = common - r * K * dfr * norm.cdf(d2) + q * S * dfq * norm.cdf(d1)
        rho = K * T * dfr * norm.cdf(d2)
    else:
        delta = -dfq * norm.cdf(-d1)
        theta = common + r * K * dfr * norm.cdf(-d2) - q * S * dfq * norm.cdf(-d1)
        rho = -K * T * dfr * norm.cdf(-d2)
    return {"delta": float(delta), "gamma": float(gamma), "vega": float(vega), "theta": float(theta), "rho": float(rho)}
