"""Generate README.md from results/summary.json (no hand-typed numbers)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
snap, inp, cnt, arb, gx = S["snapshot"], S["inputs"], S["counts"], S["arbitrage"], S["greeks_example"]
sl = S["slices"]


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


rows = "\n".join(
    f"| {s['expiry']} | {s['days']} | {s['n_quotes']} | {pct(s['atm_iv'])} | {pct(s['iv_90'])} | {pct(s['iv_110'])} | "
    f"{s['skew_90_110'] * 100:.2f} | {s['fit_rmse_vol'] * 100:.2f} | {'yes' if s['butterfly_ok'] else 'NO'} |" for s in sl)
pairs = "; ".join(f"{p['near']} -> {p['far']}: {p['points']} points, log-moneyness {p['k_min']:.2f} to {p['k_max']:.2f}"
                  for p in arb["calendar_pairs"]) or "none"
lo = min(sl, key=lambda s: s["atm_iv"])
greek_rows = "\n".join(f"| {g} | {gx['call'][g]:.4f} | {gx['put'][g]:.4f} |" for g in ("delta", "gamma", "vega", "theta", "rho"))
text = f"""# options-vol-surface

Black-Scholes pricing and Greeks, implied-volatility solving, and an **SVI-fitted implied-volatility surface** for
{snap['ticker']} from a real option-chain snapshot (close of {snap['asof_close_date']}), with butterfly and calendar
arbitrage checks. Every number below is generated from `results/summary.json` by `scripts/build_readme.py` and pinned
by tests.

## Headline

- {cnt['iv_solved']} out-of-the-money quotes across {cnt['slices_fitted']} expiries ({sl[0]['days']} to {sl[-1]['days']} days),
  spot ${snap['spot_close']:.2f}.
- ATM implied vol term structure runs from {pct(sl[0]['atm_iv'])} ({sl[0]['days']}d) to {pct(sl[-1]['atm_iv'])}
  ({sl[-1]['days']}d), lowest at {pct(lo['atm_iv'])} ({lo['days']}d).
- Put skew (IV at 90% minus 110% moneyness) falls from {sl[0]['skew_90_110'] * 100:.2f} vol points at
  {sl[0]['days']}d to {sl[-1]['skew_90_110'] * 100:.2f} at {sl[-1]['days']}d.
- SVI fit error (RMSE) is {min(s['fit_rmse_vol'] for s in sl) * 100:.2f} to {max(s['fit_rmse_vol'] for s in sl) * 100:.2f}
  vol points per slice. Butterfly-arbitrage-free (Gatheral g >= 0) on {arb['butterfly_ok_slices']} of {len(sl)} slices.
- Calendar check: total variance decreases with maturity at {arb['calendar_violations']} of {arb['calendar_grid_points']}
  grid points (log-moneyness -0.30 to 0.30), {arb['calendar_violations_in_quoted_range']} of them inside the strikes actually
  quoted for both expiries, so they come from SVI extrapolation in the upside call wing: {pairs}.
  Slices are fitted independently, so this is reported, not hidden.

| Expiry | Days | Quotes | ATM IV | IV 90% | IV 110% | Skew (vol pts) | SVI RMSE (vol pts) | No butterfly arb |
|---|---|---|---|---|---|---|---|---|
{rows}

### Greeks example: {gx['days']}-day, strike {gx['strike']}, SVI vol {pct(gx['svi_vol'])}, call price ${gx['call_price']:.2f}

Vega and rho per 1.00 change, theta per year.

| Greek | Call | Put |
|---|---|---|
{greek_rows}

## Method

- Inputs: rate {pct(inp['rate'])} ({inp['rate_source']}); dividend yield {pct(inp['div_yield'])} (trailing-12-month
  cash dividends / spot, continuous). Forward F = S e^((r-q)T); log-moneyness k = ln(K/F).
- Filters: last trade on {S['filters']['trade_date']}, price >= ${S['filters']['min_price']}, volume > 0, OTM only,
  |k| <= {S['filters']['max_abs_log_moneyness']}, at least {S['filters']['min_days']} days.
- IV: Brent root-finding on Black-Scholes-Merton, rejecting prices outside no-arbitrage bounds.
- SVI: raw parameterisation w(k) = a + b(rho(k-m) + sqrt((k-m)^2 + sigma^2)), least squares on total variance.

## Data limits (read before reusing)

- yfinance option chains are **current-only**: there is no historical chain, so this is a single frozen snapshot
  (taken {snap['snapshot_utc']} UTC) and cannot be re-downloaded. `make fetch` would produce a different date.
- The snapshot was taken outside market hours, so bid/ask were 0 for most contracts ({cnt['raw_with_positive_bid']} of
  {cnt['contracts_raw']} had a bid). IVs use **last-trade prices**, which are not synchronous with the spot close.
- A flat short rate and a trailing dividend yield are approximations; no put-call-parity forward is implied.

## Reproduce

```bash
pip install -e .[dev]
make all      # verify hashes, run analysis, rebuild README, ruff, pytest (offline)
```
"""
(ROOT / "README.md").write_text(text)
print("README.md written")
