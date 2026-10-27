"""Clean the snapshot, solve IVs, fit SVI per expiry, check arbitrage; write results/."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import bs, data, svi
from .iv import implied_vol

OUT = Path(__file__).resolve().parents[2] / "results"
MIN_PRICE = 0.05
K_RANGE = 0.35       # |log(K/F)| kept
MIN_T_DAYS = 5
GRID = np.linspace(-0.3, 0.3, 121)


def clean(c: pd.DataFrame, S: float, r: float, q: float) -> pd.DataFrame:
    m = data.meta()
    c = c[(c["trade_date"] == m["asof_close_date"]) & (c["lastPrice"] >= MIN_PRICE) & (c["volume"] > 0)
          & (c["T"] * 365 >= MIN_T_DAYS)].copy()
    c["F"] = S * np.exp((r - q) * c["T"])
    c["k"] = np.log(c["strike"] / c["F"])
    otm = ((c["type"] == "call") & (c["k"] >= 0)) | ((c["type"] == "put") & (c["k"] < 0))
    return c[otm & (c["k"].abs() <= K_RANGE)].reset_index(drop=True)


def main() -> dict:
    OUT.mkdir(exist_ok=True)
    m = data.meta()
    S, r, q = m["spot_close"], m["rate_13w_tbill_irx"], data.dividend_yield()
    raw = data.chain()
    c = clean(raw, S, r, q)
    c["iv"] = [implied_vol(p, S, K, T, r, q, t) for p, K, T, t in zip(c["lastPrice"], c["strike"], c["T"], c["type"],
                                                                         strict=True)]
    solved = c.dropna(subset=["iv"]).copy()
    solved["w"] = solved["iv"] ** 2 * solved["T"]
    slices, params = [], []
    for exp, g in solved.groupby("expiry"):
        if len(g) < 8:
            continue
        T = float(g["T"].iloc[0])
        p = svi.fit(g["k"].to_numpy(), g["w"].to_numpy())
        fit_iv = np.sqrt(svi.total_var(g["k"].to_numpy(), **p) / T)
        rmse = float(np.sqrt(np.mean((fit_iv - g["iv"].to_numpy()) ** 2)))
        kk = np.linspace(g["k"].min(), g["k"].max(), 200)
        gmin = float(svi.g_function(kk, p).min())
        iv_at = lambda x, p=p, T=T: float(np.sqrt(svi.total_var(np.log(x), **p) / T))  # noqa: E731
        slices.append({"k_quoted_min": float(g["k"].min()), "k_quoted_max": float(g["k"].max()),
                       "expiry": exp.date().isoformat(), "days": int(round(T * 365)), "n_quotes": int(len(g)),
                       "atm_iv": iv_at(1.0), "iv_90": iv_at(0.9), "iv_110": iv_at(1.1),
                       "skew_90_110": iv_at(0.9) - iv_at(1.1), "fit_rmse_vol": rmse,
                       "butterfly_min_g": gmin, "butterfly_ok": gmin >= 0, "svi": p})
        params.append(p)
        solved.loc[g.index, "svi_iv"] = fit_iv
    cal = svi.calendar_violations(params, GRID)
    # violations whose k is inside both expiries' quoted strikes
    ws = np.array([svi.total_var(GRID, **p) for p in params])
    cal_in = 0
    for i, d in enumerate(np.diff(ws, axis=0)):
        lo = max(slices[i]["k_quoted_min"], slices[i + 1]["k_quoted_min"])
        hi = min(slices[i]["k_quoted_max"], slices[i + 1]["k_quoted_max"])
        cal_in += int(((d < -1e-6) & (GRID >= lo) & (GRID <= hi)).sum())
    s30 = min(slices, key=lambda s: abs(s["days"] - 30))
    T30 = s30["days"] / 365
    F30 = S * np.exp((r - q) * T30)
    K = round(F30)
    vol = float(np.sqrt(svi.total_var(np.log(K / F30), **s30["svi"]) / T30))
    res = {
        "snapshot": {k: m[k] for k in ("ticker", "asof_close_date", "spot_close", "snapshot_utc", "source")},
        "inputs": {"rate": r, "rate_source": "13-week T-bill (^IRX), flat across maturities", "div_yield": q},
        "filters": {"trade_date": m["asof_close_date"], "min_price": MIN_PRICE, "max_abs_log_moneyness": K_RANGE,
                    "min_days": MIN_T_DAYS, "otm_only": True, "price_used": "lastPrice (bid/ask mostly 0 in snapshot)"},
        "counts": {"contracts_raw": int(len(raw)), "after_filters": int(len(c)), "iv_solved": int(len(solved)),
                   "iv_failed": int(len(c) - len(solved)), "slices_fitted": len(slices),
                   "raw_with_positive_bid": int((raw["bid"] > 0).sum())},
        "slices": slices,
        "arbitrage": {"butterfly_ok_slices": sum(s["butterfly_ok"] for s in slices), "calendar_violations": cal,
                      "calendar_violations_in_quoted_range": cal_in,
                      "calendar_grid_points": int(len(GRID) * (len(params) - 1)),
                      "calendar_pairs": [dict(v, near=slices[v["pair"]]["expiry"], far=slices[v["pair"] + 1]["expiry"])
                                         for v in svi.calendar_violations_by_pair(params, GRID)]},
        "greeks_example": {"expiry": s30["expiry"], "days": s30["days"], "strike": K, "svi_vol": vol,
                           "call_price": float(bs.price(S, K, T30, r, q, vol, "call")),
                           "call": bs.greeks(S, K, T30, r, q, vol, "call"),
                           "put": bs.greeks(S, K, T30, r, q, vol, "put")},
    }
    solved.drop(columns=["contractSymbol", "currency", "contractSize"]).to_csv(OUT / "iv_points.csv", index=False,
                                                                               float_format="%.6f")
    (OUT / "summary.json").write_text(json.dumps(res, indent=2) + "\n")
    return res


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["counts"]), json.dumps(o["arbitrage"]))
    for s in o["slices"]:
        print(s["expiry"], s["days"], s["n_quotes"], f"ATM {s['atm_iv']:.4f} skew {s['skew_90_110']:.4f} "
              f"rmse {s['fit_rmse_vol']:.4f} g {s['butterfly_min_g']:.4f}")
    print(o["greeks_example"])
