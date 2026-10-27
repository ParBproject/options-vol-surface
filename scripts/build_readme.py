"""Write README.md from results/summary.json and the frozen snapshot metadata."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
META = json.loads((ROOT / "data" / "raw" / "meta.json").read_text())
MANIFEST = json.loads((ROOT / "data" / "MANIFEST.json").read_text())
snap, inp, cnt, arb, gx = S["snapshot"], S["inputs"], S["counts"], S["arbitrage"], S["greeks_example"]
sl = S["slices"]
K90, K110 = math.log(0.9), math.log(1.1)


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def inside(s: dict, k: float) -> bool:
    return s["k_quoted_min"] <= k <= s["k_quoted_max"]


def marked(s: dict, text: str, *ks: float) -> str:
    return text if all(inside(s, k) for k in ks) else text + "†"


rows = "\n".join(
    "| {expiry} | {days} | {n} | {atm} | {iv90} | {iv110} | {skew} | {rmse:.2f} | {g} |".format(
        expiry=s["expiry"],
        days=s["days"],
        n=s["n_quotes"],
        atm=marked(s, pct(s["atm_iv"]), 0.0),
        iv90=marked(s, pct(s["iv_90"]), K90),
        iv110=marked(s, pct(s["iv_110"]), K110),
        skew=marked(s, f"{s['skew_90_110'] * 100:.2f}", K90, K110),
        rmse=s["fit_rmse_vol"] * 100,
        g="yes" if s["butterfly_ok"] else "no",
    )
    for s in sl
)
pairs = "; ".join(
    f"{p['near']} -> {p['far']}: {p['points']} points, log-moneyness {p['k_min']:.2f} to {p['k_max']:.2f}"
    for p in arb["calendar_pairs"]
) or "none"
lo = min(sl, key=lambda s: s["atm_iv"])
greek_rows = "\n".join(
    f"| {g} | {gx['call'][g]:.4f} | {gx['put'][g]:.4f} |" for g in ("delta", "gamma", "vega", "theta", "rho")
)
n_chain = sum(1 for f in MANIFEST if f.endswith(("_call.csv", "_put.csv")))
ext110 = [s for s in sl if not inside(s, K110)]
ext110_txt = " and ".join(f"{s['days']}d" for s in ext110)
skew_extra = ""
if ext110:
    skew_extra = (
        f" On {ext110_txt}, K/F = 1.1 is past the last quoted call, so that side of the skew is the fitted wing."
    )
if arb["calendar_violations_in_quoted_range"] == 0:
    cal_where = "None of them are inside the strikes quoted on both expiries; they sit in the extrapolated call wing"
else:
    cal_where = (
        f"{arb['calendar_violations_in_quoted_range']} of them are inside the strikes quoted on both expiries; "
        "the rest sit in the extrapolated call wing"
    )
wing_notes = []
for s in sl:
    missing = [name for name, k in (("ATM", 0.0), ("90%", K90), ("110%", K110)) if not inside(s, k)]
    if missing:
        wing_notes.append(f"{s['expiry']} ({', '.join(missing)})")
star = ""
if wing_notes:
    star = (
        "\n† Outside the quoted strikes for that expiry ("
        + "; ".join(wing_notes)
        + "). Those cells are the fitted wing, not a traded vol.\n"
    )

text = f"""# options-vol-surface

[![CI](https://github.com/ParBproject/options-vol-surface/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ParBproject/options-vol-surface/actions/workflows/ci.yml)

Black-Scholes prices and Greeks, implied volatility, and a raw SVI fit to {snap['ticker']} options
from the {snap['asof_close_date']} close, with butterfly and calendar checks.
`scripts/build_readme.py` writes the figures below from `results/summary.json`.

**Live app: [parbproject.github.io/options-vol-surface](https://parbproject.github.io/options-vol-surface/)**

![Demo](docs/img/demo.gif)

| Desktop | Mobile |
|---|---|
| ![Overview](docs/img/overview.png) | ![Mobile](docs/img/mobile.png) |

| Greeks explorer | Calendar check |
|---|---|
| ![Greeks](docs/img/greeks.png) | ![Arbitrage](docs/img/arbitrage.png) |

## Results

- {cnt['iv_solved']} out-of-the-money quotes across {cnt['slices_fitted']} expiries
  ({sl[0]['days']} to {sl[-1]['days']} days), spot ${snap['spot_close']:.2f}.
- SVI vol at the forward is {pct(sl[0]['atm_iv'])} at {sl[0]['days']}d and {pct(sl[-1]['atm_iv'])}
  at {sl[-1]['days']}d. The low is {pct(lo['atm_iv'])} at {lo['days']}d.
- Skew, SVI vol at 90% of the forward minus SVI vol at 110%, is {sl[0]['skew_90_110'] * 100:.2f}
  vol points at {sl[0]['days']}d and {sl[-1]['skew_90_110'] * 100:.2f} at {sl[-1]['days']}d.{skew_extra}
- SVI RMSE is {min(s['fit_rmse_vol'] for s in sl) * 100:.2f} to {max(s['fit_rmse_vol'] for s in sl) * 100:.2f}
  vol points per expiry. Gatheral's g(k) is non-negative on {arb['butterfly_ok_slices']} of {len(sl)} slices,
  on the strikes that were quoted.
- Total variance falls with maturity at {arb['calendar_violations']} of {arb['calendar_grid_points']}
  grid points (log-moneyness -0.30 to 0.30). {cal_where}: {pairs}.
  Each expiry is fit on its own.

ATM, 90% and 110% in the table are SVI vols at K/F = 1, 0.9 and 1.1, not raw quotes.
{star}
| Expiry | Days | Quotes | SVI ATM | SVI 90% | SVI 110% | Skew (vol pts) | SVI RMSE (vol pts) | g(k) >= 0 |
|---|---|---|---|---|---|---|---|---|
{rows}

### Greeks, {gx['days']}-day expiry, strike {gx['strike']}, SVI vol {pct(gx['svi_vol'])}, call ${gx['call_price']:.2f}

Vega and rho are for a 1.00 move in vol or rate. Theta is per year.

| Greek | Call | Put |
|---|---|---|
{greek_rows}

## Data provenance

- **Option chain:** {META['ticker']} calls and puts for {len(META['expiries'])} expiries
  ({META['expiries'][0]} to {META['expiries'][-1]}), source: {META['source']}.
  Snapshot taken {META['snapshot_utc']} (UTC). Quotes are last trades on the {META['asof_close_date']} close.
- **Spot and rates:** SPY close {META['spot_close']:.2f}; 13-week T-bill (^IRX) {META['rate_13w_tbill_irx'] * 100:.2f}%;
  trailing-12-month dividends ${META['trailing_12m_dividends']:.3f} from {META['n_dividends']} payments (Yahoo Finance).
- **Frozen snapshot:** {len(MANIFEST)} files in `data/raw/` ({n_chain} chain CSVs plus `meta.json`),
  each SHA-256 hashed in `data/MANIFEST.json`. `make all` checks the hashes and fails if a file has changed.
- **Not historical:** Yahoo serves only the current chain, so this snapshot cannot be downloaded again.
  `make fetch` takes a new snapshot and changes the hashes and the results.
- **Terms:** the snapshot is in the repo so the study can be rerun. Check Yahoo's terms before using it for anything else.

## Method

- Rate {pct(inp['rate'])} ({inp['rate_source']}). Dividend yield {pct(inp['div_yield'])},
  log(1 + trailing-12-month dividends / spot). Forward F = S e^((r-q)T); log-moneyness k = ln(K/F).
  `meta.json` also stores the 10-year yield; the fit does not use it.
- Filters: last trade on {S['filters']['trade_date']}, price >= ${S['filters']['min_price']}, volume > 0,
  out-of-the-money only, |k| <= {S['filters']['max_abs_log_moneyness']}, at least {S['filters']['min_days']} days.
- IV: Brent on Black-Scholes-Merton. Prices outside the no-arbitrage bounds are dropped.
- SVI: raw total variance w(k) = a + b(rho(k-m) + sqrt((k-m)^2 + sigma^2)), least squares, one fit per expiry.
- The page recomputes prices, Greeks, SVI vols and the calendar grid in `web/src/volmath.js`.
  `web/tests/volmath.test.js` checks them against `results/summary.json`.

## Limits

- yfinance option chains are **current-only**: there is no historical chain, so this is one frozen snapshot
  (taken {snap['snapshot_utc']} UTC) and cannot be downloaded again. `make fetch` would be a different date.
- The snapshot was taken outside market hours, so bid and ask were 0 for most contracts
  ({cnt['raw_with_positive_bid']} of {cnt['contracts_raw']} had a bid). IVs use last-trade prices, which are not
  the same time as the spot close. Yahoo's own `impliedVolatility` column is not used; with a zero bid it is
  often a placeholder.
- The short rate is flat, and the dividend yield is a trailing cash yield. There is no put-call-parity forward.

## Reproduce

```bash
pip install -e .[dev]
make all      # verify hashes, run analysis, rebuild README, ruff, pytest (offline)
make web      # export app data, run Node parity tests, build the React app (Node 20+)
make deploy   # publish web/dist to the gh-pages branch
```
"""
(ROOT / "README.md").write_text(text)
print("README.md written")
