"""Pin headline numbers so any change to data or method shows up in review."""
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
PINNED_ATM = {  # expiry: ATM IV
    "2026-10-29": 0.1575,
    "2026-11-06": 0.1584,
    "2026-11-20": 0.1499,
    "2026-11-30": 0.1452,
    "2026-12-18": 0.1513,
    "2027-01-15": 0.1511,
    "2027-02-19": 0.1540,
    "2027-03-31": 0.1577,
    "2027-06-30": 0.1643,
    "2027-09-30": 0.1718,
    "2028-06-16": 0.1839,
}


def test_counts():
    assert S["counts"]["contracts_raw"] == 3682
    assert S["counts"]["iv_solved"] == 1077
    assert S["counts"]["slices_fitted"] == 11


@pytest.mark.parametrize("expiry", list(PINNED_ATM))
def test_atm_iv_pinned(expiry):
    s = next(x for x in S["slices"] if x["expiry"] == expiry)
    assert s["atm_iv"] == pytest.approx(PINNED_ATM[expiry], abs=5e-4)
    assert s["fit_rmse_vol"] < 0.01


def test_arbitrage_pinned():
    a = S["arbitrage"]
    assert a["butterfly_ok_slices"] == 11
    assert a["calendar_violations"] == 49
    assert all(p["k_min"] > 0 for p in a["calendar_pairs"])  # only the upside call wing


def test_greeks_example_parity():
    g = S["greeks_example"]
    assert g["call"]["gamma"] == pytest.approx(g["put"]["gamma"])
    assert g["call"]["delta"] - g["put"]["delta"] == pytest.approx(
        math.exp(-S["inputs"]["div_yield"] * g["days"] / 365), abs=1e-9)


def test_readme_generated_from_results():
    readme = (ROOT / "README.md").read_text()
    for s in S["slices"]:
        assert f"{s['atm_iv'] * 100:.2f}%" in readme
    assert "current-only" in readme
