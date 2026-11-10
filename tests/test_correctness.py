"""Closed-form checks for Black-Scholes, implied vol, raw SVI, and arbitrage.

The other method tests check internal consistency: put-call parity holds for any
d1/d2, and the Greek and IV tests only compare a function with itself. These pin
the formulas to textbook and hand-computed values.
"""
import math

import numpy as np
import pytest

from volsurf import bs, svi
from volsurf.iv import implied_vol


def _ncdf(x: float) -> float:
    """Standard normal CDF from libm's erf, not scipy.stats.norm (which bs.py uses)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# Φ(0.1) and n(0.1). The zero-rate case has d1 = 0.1 and d2 = -0.1 exactly.
_PHI_01 = _ncdf(0.1)
_N_01 = _npdf(0.1)


def _bs_reference(S, K, T, r, q, vol, kind):
    """Textbook Black-Scholes-Merton evaluated with math.erf, not volsurf.bs."""
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * vol * vol) * T) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t
    dfq, dfr = math.exp(-q * T), math.exp(-r * T)
    pdf = _npdf(d1)
    gamma = dfq * pdf / (S * vol * sqrt_t)
    vega = S * dfq * pdf * sqrt_t
    common = -S * dfq * pdf * vol / (2.0 * sqrt_t)
    if kind == "call":
        price = S * dfq * _ncdf(d1) - K * dfr * _ncdf(d2)
        delta = dfq * _ncdf(d1)
        theta = common - r * K * dfr * _ncdf(d2) + q * S * dfq * _ncdf(d1)
        rho = K * T * dfr * _ncdf(d2)
    else:
        price = K * dfr * _ncdf(-d2) - S * dfq * _ncdf(-d1)
        delta = -dfq * _ncdf(-d1)
        theta = common + r * K * dfr * _ncdf(-d2) - q * S * dfq * _ncdf(-d1)
        rho = -K * T * dfr * _ncdf(-d2)
    return price, {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


def test_black_scholes_zero_rate_atm_closed_form():
    # S = K, T = 1, r = q = 0 => d1 = σ/2, d2 = -σ/2.
    # Call = put = S * (2 Φ(σ/2) - 1). Greeks reduce to Φ and n at that point.
    S, K, T, r, q, vol = 100.0, 100.0, 1.0, 0.0, 0.0, 0.2
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    premium = S * (2 * _PHI_01 - 1)
    assert call == pytest.approx(premium, abs=1e-12)
    assert put == pytest.approx(premium, abs=1e-12)
    # 100 * (2 Φ(0.1) - 1), from the Φ above rather than from bs.price.
    assert premium == pytest.approx(7.965567455406, abs=1e-12)

    call_g = bs.greeks(S, K, T, r, q, vol, "call")
    put_g = bs.greeks(S, K, T, r, q, vol, "put")
    gamma = _N_01 / (S * vol)
    vega = S * _N_01
    theta = -S * _N_01 * vol / 2
    assert call_g == pytest.approx(
        {"delta": _PHI_01, "gamma": gamma, "vega": vega, "theta": theta, "rho": K * (1 - _PHI_01)}, abs=1e-12
    )
    assert put_g == pytest.approx(
        {"delta": _PHI_01 - 1, "gamma": gamma, "vega": vega, "theta": theta, "rho": -K * _PHI_01}, abs=1e-12
    )


def test_black_scholes_haug_textbook():
    # Espen Haug, The Complete Guide to Option Pricing Formulas: European option
    # with S=60, K=65, T=0.25, r=0.08, b=r (so q=0), σ=0.30. Published prices
    # are 2.1334 (call) and 5.8463 (put).
    S, K, T, r, q, vol = 60.0, 65.0, 0.25, 0.08, 0.0, 0.30
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    ref_call, _ = _bs_reference(S, K, T, r, q, vol, "call")
    ref_put, _ = _bs_reference(S, K, T, r, q, vol, "put")
    assert ref_call == pytest.approx(2.1334, abs=5e-5)
    assert ref_put == pytest.approx(5.8463, abs=5e-5)
    assert call == pytest.approx(ref_call, abs=1e-12)
    assert put == pytest.approx(ref_put, abs=1e-12)
    assert call - put == pytest.approx(S - K * math.exp(-r * T), abs=1e-12)
    assert implied_vol(call, S, K, T, r, q, "call") == pytest.approx(vol, abs=1e-10)
    assert implied_vol(put, S, K, T, r, q, "put") == pytest.approx(vol, abs=1e-10)


def test_black_scholes_hull_textbook():
    # Hull, Options, Futures, and Other Derivatives: European call on a
    # non-dividend-paying stock, S=49, K=50, r=0.05, σ=0.20, T=20/52.
    # The text rounds the price to 2.40.
    S, K, T, r, q, vol = 49.0, 50.0, 20 / 52, 0.05, 0.0, 0.20
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    ref_call, _ = _bs_reference(S, K, T, r, q, vol, "call")
    ref_put, _ = _bs_reference(S, K, T, r, q, vol, "put")
    assert ref_call == pytest.approx(2.4005, abs=5e-5)
    assert call == pytest.approx(ref_call, abs=1e-12)
    assert put == pytest.approx(ref_put, abs=1e-12)
    assert call - put == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-12)


def test_black_scholes_with_dividend_yield():
    # q > 0, so this is not the textbook q = 0 case. Expected values come from
    # the erf reference above, not from a table copied out of bs.price.
    S, K, T, r, q, vol = 100.0, 95.0, 0.75, 0.03, 0.015, 0.25
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    ref_call, ref_call_g = _bs_reference(S, K, T, r, q, vol, "call")
    ref_put, ref_put_g = _bs_reference(S, K, T, r, q, vol, "put")
    assert call == pytest.approx(ref_call, abs=1e-12)
    assert put == pytest.approx(ref_put, abs=1e-12)
    assert call - put == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-12)
    assert bs.greeks(S, K, T, r, q, vol, "call") == pytest.approx(ref_call_g, abs=1e-12)
    assert bs.greeks(S, K, T, r, q, vol, "put") == pytest.approx(ref_put_g, abs=1e-12)


def test_iv_round_trip_across_moneyness_and_maturity():
    S, r, q = 100.0, 0.03, 0.01
    for kind in ("call", "put"):
        for T in (0.25, 0.75, 1.5):
            for moneyness in (0.8, 0.9, 1.0, 1.1, 1.25):
                for vol in (0.10, 0.25, 0.55):
                    K = S * moneyness
                    px = float(bs.price(S, K, T, r, q, vol, kind))
                    got = implied_vol(px, S, K, T, r, q, kind)
                    assert got == pytest.approx(vol, abs=1e-8), (kind, K, T, vol, got)


def test_iv_deep_itm_and_otm_round_trip():
    # Far enough that the time value is still a normal float. Short-dated
    # options struck much further in collapse onto intrinsic and have no vol.
    S, r, q = 100.0, 0.02, 0.01
    cases = (
        ("call", 40.0, 1.0, 0.25),  # deep ITM
        ("call", 250.0, 1.0, 0.50),  # deep OTM
        ("put", 180.0, 1.0, 0.25),  # deep ITM
        ("put", 30.0, 0.5, 0.40),  # deep OTM
        ("call", 70.0, 0.1, 0.40),  # short-dated ITM, time value still visible
    )
    for kind, K, T, vol in cases:
        px = float(bs.price(S, K, T, r, q, vol, kind))
        assert implied_vol(px, S, K, T, r, q, kind) == pytest.approx(vol, abs=1e-8)


@pytest.mark.parametrize("kind,strike", [("call", 90.0), ("put", 110.0), ("call", 105.0), ("put", 105.0)])
def test_iv_rejects_prices_outside_bounds(kind, strike):
    S, T, r, q = 100.0, 0.5, 0.02, 0.01
    K = strike
    # Same exp as implied_vol, so "exactly at intrinsic" is that function's bound
    # and not one ulp above it.
    df_s, df_k = np.exp(-q * T), np.exp(-r * T)
    raw = S * df_s - K * df_k if kind == "call" else K * df_k - S * df_s
    intrinsic = max(raw, 0.0)
    upper = S * df_s if kind == "call" else K * df_k
    # Strictly outside the no-arbitrage interval. These have no volatility.
    for price in (intrinsic - 0.05, upper + 0.05, -1.0):
        assert math.isnan(implied_vol(price, S, K, T, r, q, kind))
    # Exactly at discounted intrinsic is the vol → 0 limit. The solver bracket
    # starts at 1e-4, so this endpoint is not inside the open interval and the
    # function returns NaN rather than 0. Separate from the violations above:
    # returning 0 here would be a reasonable later change, not a broken check.
    assert math.isnan(implied_vol(intrinsic, S, K, T, r, q, kind))
    # The upper bound is reached only as vol → ∞, so no finite vol is returned.
    assert math.isnan(implied_vol(upper, S, K, T, r, q, kind))
    inside = float(bs.price(S, K, T, r, q, 0.22, kind))
    assert intrinsic < inside < upper
    assert implied_vol(inside, S, K, T, r, q, kind) == pytest.approx(0.22, abs=1e-8)


def test_svi_total_variance_hand_values():
    # w(k) = a + b (ρ(k-m) + sqrt((k-m)^2 + σ^2))
    # ρ = m = 0, σ = 0.2, k = 0 -> w = a + b σ = 0.06
    assert svi.total_var(0.0, 0.04, 0.1, 0.0, 0.0, 0.2) == pytest.approx(0.06, abs=1e-12)
    # k = 0.1 -> sqrt(0.01 + 0.04) = sqrt(0.05)
    assert svi.total_var(0.1, 0.04, 0.1, 0.0, 0.0, 0.2) == pytest.approx(0.04 + 0.1 * math.sqrt(0.05), abs=1e-12)
    # k = 0, m = 0.05, ρ = -0.4 -> x = -0.05, ρ x = 0.02, sqrt(0.0425)
    assert svi.total_var(0.0, 0.04, 0.1, -0.4, 0.05, 0.2) == pytest.approx(
        0.04 + 0.1 * (0.02 + math.sqrt(0.0425)), abs=1e-12
    )


def test_svi_fit_recovers_parameters():
    true = {"a": 0.04, "b": 0.15, "rho": -0.4, "m": 0.05, "sigma": 0.2}
    k = np.linspace(-0.5, 0.5, 51)
    w = svi.total_var(k, **true)
    fit = svi.fit(k, w)
    for name, value in true.items():
        assert fit[name] == pytest.approx(value, abs=1e-6)
    assert np.allclose(svi.total_var(k, **fit), w, atol=1e-8)


def test_g_function_hand_value_and_butterfly_violation():
    # ρ = m = 0. At k = 0, w' = 0 and w'' = b/σ, so g = 1 + w''/2 = 1 + b/(2σ) = 1.25.
    smile = {"a": 0.04, "b": 0.1, "rho": 0.0, "m": 0.0, "sigma": 0.2}
    assert float(svi.g_function(np.array([0.0]), smile)[0]) == pytest.approx(1.25, abs=1e-12)
    # Same parameters at k = 0.3, from w, w', w'' plugged into Gatheral's g.
    assert float(svi.g_function(np.array([0.3]), smile)[0]) == pytest.approx(0.7182077222233495, abs=1e-12)
    assert svi.g_function(np.linspace(-0.5, 0.5, 201), smile).min() > 0

    # Lee's moment bound: the raw-SVI wing slopes are b(1±ρ). b(1+|ρ|) = 2.85 > 2,
    # so this slice cannot be free of butterfly arbitrage.
    steep = {"a": 0.04, "b": 1.5, "rho": -0.9, "m": 0.0, "sigma": 0.1}
    assert steep["b"] * (1 + abs(steep["rho"])) > 2
    assert svi.g_function(np.linspace(-1.0, 1.0, 401), steep).min() < 0


def _flat_smile(k, a, b, sigma):
    """Raw SVI with ρ = m = 0: w(k) = a + b sqrt(k^2 + σ^2)."""
    return a + b * np.sqrt(np.asarray(k, dtype=float) ** 2 + sigma**2)


def test_calendar_flags_a_crossing_and_passes_a_clean_surface():
    # ρ = m = 0, so w(0) = a + b σ and the wings share sqrt(k^2 + σ^2).
    wing = math.sqrt(0.25**2 + 0.1**2)
    near = {"a": 0.02, "b": 0.3, "rho": 0.0, "m": 0.0, "sigma": 0.1}
    far = {"a": 0.05, "b": 0.02, "rho": 0.0, "m": 0.0, "sigma": 0.1}
    assert svi.total_var(0.0, **near) == pytest.approx(0.05, abs=1e-12)
    assert svi.total_var(0.0, **far) == pytest.approx(0.052, abs=1e-12)
    assert svi.total_var(0.25, **near) == pytest.approx(0.02 + 0.3 * wing, abs=1e-12)
    assert svi.total_var(-0.25, **far) == pytest.approx(0.05 + 0.02 * wing, abs=1e-12)

    # w_far - w_near = 0.03 - 0.28 sqrt(k^2 + σ^2), so the far expiry is above
    # the near one only for |k| below this threshold and below it outside.
    sigma = 0.1
    threshold = math.sqrt((0.03 / 0.28) ** 2 - sigma**2)
    grid = np.linspace(-0.4, 0.4, 401)
    hand_near = _flat_smile(grid, 0.02, 0.3, sigma)
    hand_far = _flat_smile(grid, 0.05, 0.02, sigma)
    assert np.allclose(svi.total_var(grid, **near), hand_near, atol=1e-12)
    assert np.allclose(svi.total_var(grid, **far), hand_far, atol=1e-12)
    violated = hand_far - hand_near < -1e-6
    assert violated[0] and violated[-1]
    assert not violated[np.abs(grid) < threshold - 1e-8].any()
    assert violated[np.abs(grid) > threshold + 1e-8].all()
    assert int(violated.sum()) > 2
    assert svi.calendar_violations([near, far], grid) == int(violated.sum())
    assert svi.calendar_violations_by_pair([near, far], grid) == [
        {
            "pair": 0,
            "points": int(violated.sum()),
            "k_min": pytest.approx(float(grid[violated].min())),
            "k_max": pytest.approx(float(grid[violated].max())),
        }
    ]

    grid = np.linspace(-0.4, 0.4, 81)
    clean_near = {"a": 0.03, "b": 0.1, "rho": -0.3, "m": 0.0, "sigma": 0.2}
    clean_far = {"a": 0.05, "b": 0.1, "rho": -0.3, "m": 0.0, "sigma": 0.2}
    assert svi.g_function(grid, clean_near).min() > 0
    assert svi.g_function(grid, clean_far).min() > 0
    assert svi.calendar_violations([clean_near, clean_far], grid) == 0
    assert svi.calendar_violations_by_pair([clean_near, clean_far], grid) == []
