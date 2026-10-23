"""The web app's exported data must be exactly the published results."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = json.loads((ROOT / "web" / "public" / "data" / "app.json").read_text())
S = json.loads((ROOT / "results" / "summary.json").read_text())


def test_same_results():
    for k in ("slices", "arbitrage", "greeks_example", "counts", "inputs"):
        assert APP[k] == S[k]


def test_quotes_match_iv_points():
    pts = pd.read_csv(ROOT / "results" / "iv_points.csv")
    assert sum(len(q["k"]) for q in APP["quotes"].values()) == len(pts) == S["counts"]["iv_solved"]
    for s in S["slices"]:
        assert len(APP["quotes"][s["expiry"]]["k"]) == s["n_quotes"]
