"""Raw SVI (Gatheral 2004) per expiry, plus butterfly and calendar arbitrage checks."""
import numpy as np
from scipy.optimize import least_squares


def total_var(k, a, b, rho, m, sigma):
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma**2))


def fit(k: np.ndarray, w: np.ndarray, weights: np.ndarray | None = None) -> dict:
    """Least-squares fit of total variance w(k); enforces b>=0, |rho|<1, sigma>0 and min w >= 0."""
    wts = np.ones_like(w) if weights is None else weights
    best = None
    for m0 in (-0.1, 0.0, 0.1):
        for s0 in (0.05, 0.2):
            x0 = [max(w.min() * 0.5, 1e-6), 0.1, -0.5, m0, s0]

            def res(x):
                a, b, rho, m, sig = x
                pen = max(0.0, -(a + b * sig * np.sqrt(1 - rho**2))) * 1e3
                return np.append(wts * (total_var(k, *x) - w), pen)

            r = least_squares(res, x0, bounds=([-1, 0, -0.999, -1, 1e-4], [1, 5, 0.999, 1, 2]))
            if best is None or r.cost < best.cost:
                best = r
    a, b, rho, m, sig = best.x
    return {"a": float(a), "b": float(b), "rho": float(rho), "m": float(m), "sigma": float(sig)}


def g_function(k: np.ndarray, p: dict) -> np.ndarray:
    """Gatheral's density condition: butterfly arbitrage-free iff g(k) >= 0."""
    a, b, rho, m, s = p["a"], p["b"], p["rho"], p["m"], p["sigma"]
    x = k - m
    rt = np.sqrt(x**2 + s**2)
    w = a + b * (rho * x + rt)
    w1 = b * (rho + x / rt)
    w2 = b * s**2 / rt**3
    return (1 - k * w1 / (2 * w)) ** 2 - w1**2 / 4 * (1 / w + 0.25) + w2 / 2


def calendar_violations(params: list[dict], k: np.ndarray, tol: float = 1e-6) -> int:
    """Count grid points where total variance decreases with maturity (params sorted by T)."""
    ws = np.array([total_var(k, **p) for p in params])
    return int((np.diff(ws, axis=0) < -tol).sum())


def calendar_violations_by_pair(params: list[dict], k: np.ndarray, tol: float = 1e-6) -> list[dict]:
    ws = np.array([total_var(k, **p) for p in params])
    out = []
    for i, d in enumerate(np.diff(ws, axis=0)):
        bad = d < -tol
        if bad.any():
            out.append({"pair": i, "points": int(bad.sum()), "k_min": float(k[bad].min()), "k_max": float(k[bad].max())})
    return out
