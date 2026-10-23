import numpy as np
import pytest

from volsurf import bs, svi
from volsurf.iv import implied_vol

S, K, T, R, Q, V = 100.0, 105.0, 0.5, 0.04, 0.012, 0.22


def test_put_call_parity():
    c, p = bs.price(S, K, T, R, Q, V, "call"), bs.price(S, K, T, R, Q, V, "put")
    assert c - p == pytest.approx(S * np.exp(-Q * T) - K * np.exp(-R * T), abs=1e-10)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_greeks_match_finite_differences(kind):
    g = bs.greeks(S, K, T, R, Q, V, kind)
    h = 1e-4
    f = lambda **kw: bs.price(**{"S": S, "K": K, "T": T, "r": R, "q": Q, "vol": V, "kind": kind, **kw})  # noqa: E731
    assert g["delta"] == pytest.approx((f(S=S + h) - f(S=S - h)) / (2 * h), rel=1e-5)
    assert g["gamma"] == pytest.approx((f(S=S + 1e-2) - 2 * f() + f(S=S - 1e-2)) / 1e-4, rel=1e-4)
    assert g["vega"] == pytest.approx((f(vol=V + h) - f(vol=V - h)) / (2 * h), rel=1e-5)
    assert g["rho"] == pytest.approx((f(r=R + h) - f(r=R - h)) / (2 * h), rel=1e-5)
    assert g["theta"] == pytest.approx(-(f(T=T + h) - f(T=T - h)) / (2 * h), rel=1e-4)


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("vol", [0.05, 0.2, 0.8])
def test_iv_round_trip(kind, vol):
    p = bs.price(S, K, T, R, Q, vol, kind)
    assert implied_vol(p, S, K, T, R, Q, kind) == pytest.approx(vol, abs=1e-7)


def test_iv_rejects_arbitrage_price():
    assert np.isnan(implied_vol(0.0001, S, 50, T, R, Q, "call"))


def test_svi_recovers_synthetic_params():
    true = {"a": 0.01, "b": 0.1, "rho": -0.6, "m": 0.02, "sigma": 0.1}
    k = np.linspace(-0.3, 0.3, 40)
    p = svi.fit(k, svi.total_var(k, **true))
    assert np.allclose(svi.total_var(k, **p), svi.total_var(k, **true), atol=1e-7)


def test_butterfly_and_calendar_checks():
    k = np.linspace(-0.5, 0.5, 101)
    ok = {"a": 0.01, "b": 0.1, "rho": -0.5, "m": 0.0, "sigma": 0.2}
    assert svi.g_function(k, ok).min() > 0
    bad = {"a": 0.0, "b": 2.0, "rho": -0.99, "m": 0.0, "sigma": 0.01}  # extreme wing slope -> negative density
    assert svi.g_function(k, bad).min() < 0
    later = dict(ok, a=0.02)
    assert svi.calendar_violations([ok, later], k) == 0
    assert svi.calendar_violations([later, ok], k) == len(k)
