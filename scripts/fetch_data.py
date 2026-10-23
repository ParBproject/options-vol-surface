"""ONLINE ONLY: snapshot SPY option chains + inputs from yfinance. Run once; outputs are frozen."""
import datetime as dt
import json
from pathlib import Path

import yfinance as yf

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
t = yf.Ticker("SPY")
hist = t.history(period="5d", auto_adjust=False)
spot = float(hist["Close"].iloc[-1])
asof = hist.index[-1].date().isoformat()
divs = t.dividends
divs = divs[divs.index >= divs.index[-1] - dt.timedelta(days=365)]
irx = yf.Ticker("^IRX").history(period="5d")["Close"].iloc[-1] / 100
tnx = yf.Ticker("^TNX").history(period="5d")["Close"].iloc[-1] / 100
today = dt.date.fromisoformat(asof)
picked = []
targets = [7, 14, 30, 45, 60, 90, 120, 180, 270, 365, 540]
exps = [dt.date.fromisoformat(e) for e in t.options]
for tg in targets:
    e = min(exps, key=lambda x: abs((x - today).days - tg))
    if e not in picked and (e - today).days >= 5:
        picked.append(e)
for e in picked:
    ch = t.option_chain(e.isoformat())
    for kind, df in (("call", ch.calls), ("put", ch.puts)):
        df = df.assign(expiry=e.isoformat(), type=kind)
        df.to_csv(RAW / f"spy_{e.isoformat()}_{kind}.csv", index=False)
meta = {
    "ticker": "SPY", "asof_close_date": asof, "spot_close": spot,
    "snapshot_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    "rate_13w_tbill_irx": float(irx), "rate_10y_tnx": float(tnx),
    "trailing_12m_dividends": float(divs.sum()), "n_dividends": int(len(divs)),
    "expiries": [e.isoformat() for e in picked],
    "source": "yfinance (Yahoo Finance), current chain snapshot; not historical",
}
(RAW / "meta.json").write_text(json.dumps(meta, indent=2))
print(json.dumps(meta, indent=2))
