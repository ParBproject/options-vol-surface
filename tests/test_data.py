import subprocess
import sys
from pathlib import Path

from volsurf import data

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_matches():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/manifest.py"), "--check"], capture_output=True)
    assert r.returncode == 0, r.stderr


def test_snapshot_meta():
    m = data.meta()
    assert m["ticker"] == "SPY" and m["asof_close_date"] == "2026-10-22"
    assert len(m["expiries"]) == 11


def test_chain_shape():
    c = data.chain()
    assert set(c["type"]) == {"call", "put"}
    assert (c["T"] > 0).all()
    assert c["strike"].gt(0).all()
    assert 0 < data.dividend_yield() < 0.03
