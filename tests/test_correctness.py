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

# Φ(0.1) and n(0.1), from the error function. Used by the zero-rate case below,
# where d1 = 0.1 and d2 = -0.1 exactly, so the price is not a fitted number.
_PHI_01 = 0.539827837277029
_N_01 = 0.396952547477012


def test_black_scholes_zero_rate_atm_closed_form():
    # S = K, T = 1, r = q = 0 => d1 = σ/2, d2 = -σ/2.
    # Call = put = S * (2 Φ(σ/2) - 1). Greeks reduce to Φ and n at that point.
    S, K, T, r, q, vol = 100.0, 100.0, 1.0, 0.0, 0.0, 0.2
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    premium = S * (2 * _PHI_01 - 1)
    assert call == pytest.approx(premium, abs=1e-12)
    assert put == pytest.approx(premium, abs=1e-12)
    assert call == pytest.approx(7.965567455406, abs=1e-12)

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
    # are 2.1334 (call) and 5.8463 (put); the extra digits are the same closed form.
    S, K, T, r, q, vol = 60.0, 65.0, 0.25, 0.08, 0.0, 0.30
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    assert call == pytest.approx(2.1334, abs=5e-5)
    assert put == pytest.approx(5.8463, abs=5e-5)
    assert call == pytest.approx(2.133368444916, abs=1e-12)
    assert put == pytest.approx(5.846282209855, abs=1e-12)
    assert call - put == pytest.approx(S - K * math.exp(-r * T), abs=1e-12)
    assert implied_vol(call, S, K, T, r, q, "call") == pytest.approx(vol, abs=1e-10)
    assert implied_vol(put, S, K, T, r, q, "put") == pytest.approx(vol, abs=1e-10)


def test_black_scholes_hull_textbook():
    # Hull, Options, Futures, and Other Derivatives: European call on a
    # non-dividend-paying stock, S=49, K=50, r=0.05, σ=0.20, T=20/52.
    # The text rounds the price to 2.40; the closed form is 2.400527323272.
    S, K, T, r, q, vol = 49.0, 50.0, 20 / 52, 0.05, 0.0, 0.20
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    assert call == pytest.approx(2.4005, abs=5e-5)
    assert call == pytest.approx(2.400527323272, abs=1e-12)
    assert put == pytest.approx(2.448175441282, abs=1e-12)
    assert call - put == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-12)


def test_black_scholes_with_dividend_yield():
    # Continuous yield, so this is not the q=0 textbook case. Digits are the
    # closed form evaluated with Φ from the error function.
    S, K, T, r, q, vol = 100.0, 95.0, 0.75, 0.03, 0.015, 0.25
    call = bs.price(S, K, T, r, q, vol, "call")
    put = bs.price(S, K, T, r, q, vol, "put")
    assert call == pytest.approx(11.604174999518, abs=1e-12)
    assert put == pytest.approx(5.609238071762, abs=1e-12)
    assert call - put == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-12)
    assert bs.greeks(S, K, T, r, q, vol, "call") == pytest.approx(
        {
            "delta": 0.647043230041,
            "gamma": 0.016838644664,
            "vega": 31.572458744721,
            "theta": -5.884516052529,
            "rho": 39.825111003408,
        },
        abs=1e-12,
    )
    assert bs.greeks(S, K, T, r, q, vol, "put") == pytest.approx(
        {
            "delta": -0.341769814571,
            "gamma": 0.016838644664,
            "vega": 31.572458744721,
            "theta": -4.581144593445,
            "rho": -29.839664646618,
        },
        abs=1e-12,
    )


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


@pytest.mark.parametrize("kind", ["call", "put"])
def test_iv_rejects_prices_at_or_outside_bounds(kind):
    S, K, T, r, q = 100.0, 105.0, 0.5, 0.02, 0.01
    df_s, df_k = math.exp(-q * T), math.exp(-r * T)
    intrinsic = max(S * df_s - K * df_k, 0.0) if kind == "call" else max(K * df_k - S * df_s, 0.0)
    upper = S * df_s if kind == "call" else K * df_k
    for price in (intrinsic - 0.05, intrinsic, upper, upper + 0.05, -1.0):
        assert math.isnan(implied_vol(price, S, K, T, r, q, kind))
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


def test_calendar_flags_a_crossing_and_passes_a_clean_surface():
    k = np.array([-0.25, 0.0, 0.25])
    # ρ = m = 0, so w(0) = a + b σ and the wings share sqrt(k^2 + σ^2).
    wing = math.sqrt(0.25**2 + 0.1**2)
    near = {"a": 0.02, "b": 0.3, "rho": 0.0, "m": 0.0, "sigma": 0.1}
    far = {"a": 0.05, "b": 0.02, "rho": 0.0, "m": 0.0, "sigma": 0.1}
    assert svi.total_var(0.0, **near) == pytest.approx(0.05, abs=1e-12)
    assert svi.total_var(0.0, **far) == pytest.approx(0.052, abs=1e-12)
    assert svi.total_var(0.25, **near) == pytest.approx(0.02 + 0.3 * wing, abs=1e-12)
    assert svi.total_var(-0.25, **far) == pytest.approx(0.05 + 0.02 * wing, abs=1e-12)
    # Far expiry is above the near one at the money and below it in both wings.
    assert svi.total_var(0.0, **far) > svi.total_var(0.0, **near)
    assert svi.total_var(0.25, **far) < svi.total_var(0.25, **near)
    assert svi.total_var(-0.25, **far) < svi.total_var(-0.25, **near)
    assert svi.calendar_violations([near, far], k) == 2
    assert svi.calendar_violations_by_pair([near, far], k) == [
        {"pair": 0, "points": 2, "k_min": pytest.approx(-0.25), "k_max": pytest.approx(0.25)}
    ]

    grid = np.linspace(-0.4, 0.4, 81)
    clean_near = {"a": 0.03, "b": 0.1, "rho": -0.3, "m": 0.0, "sigma": 0.2}
    clean_far = {"a": 0.05, "b": 0.1, "rho": -0.3, "m": 0.0, "sigma": 0.2}
    assert svi.g_function(grid, clean_near).min() > 0
    assert svi.g_function(grid, clean_far).min() > 0
    assert svi.calendar_violations([clean_near, clean_far], grid) == 0
    assert svi.calendar_violations_by_pair([clean_near, clean_far], grid) == []
