"""Offline loaders for the frozen SPY option-chain snapshot in data/raw."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"


def meta() -> dict:
    return json.loads((RAW / "meta.json").read_text())


def chain() -> pd.DataFrame:
    """All snapshotted contracts with year fraction T (ACT/365 from the as-of close)."""
    m = meta()
    frames = [pd.read_csv(p) for p in sorted(RAW.glob("spy_*_*.csv"))]
    df = pd.concat(frames, ignore_index=True)
    asof = pd.Timestamp(m["asof_close_date"])
    df["expiry"] = pd.to_datetime(df["expiry"])
    df["T"] = (df["expiry"] - asof).dt.days / 365.0
    df["trade_date"] = df["lastTradeDate"].str[:10]
    return df


def dividend_yield() -> float:
    """Continuous yield from trailing-12-month cash dividends / spot."""
    m = meta()
    return float(np.log1p(m["trailing_12m_dividends"] / m["spot_close"]))
