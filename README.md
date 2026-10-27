# options-vol-surface

[![CI](https://github.com/ParBproject/options-vol-surface/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ParBproject/options-vol-surface/actions/workflows/ci.yml)

Black-Scholes prices and Greeks, implied volatility, and a raw SVI fit to SPY options
from the 2026-10-22 close, with butterfly and calendar checks.
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

- 1077 out-of-the-money quotes across 11 expiries
  (7 to 603 days), spot $763.96.
- SVI vol at the forward is 15.75% at 7d and 18.39%
  at 603d. The low is 14.52% at 39d.
- Skew, SVI vol at 90% of the forward minus SVI vol at 110%, is 26.12
  vol points at 7d and 3.24 at 603d. On 7d and 15d, K/F = 1.1 is past the last quoted call, so that side of the skew is the fitted wing.
- SVI RMSE is 0.22 to 0.67
  vol points per expiry. Gatheral's g(k) is non-negative on 11 of 11 slices,
  on the strikes that were quoted.
- Total variance falls with maturity at 49 of 1210
  grid points (log-moneyness -0.30 to 0.30). None of them are inside the strikes quoted on both expiries; they sit in the extrapolated call wing: 2026-11-30 -> 2026-12-18: 27 points, log-moneyness 0.17 to 0.30; 2027-01-15 -> 2027-02-19: 16 points, log-moneyness 0.23 to 0.30; 2027-03-31 -> 2027-06-30: 6 points, log-moneyness 0.28 to 0.30.
  Each expiry is fit on its own.

ATM, 90% and 110% in the table are SVI vols at K/F = 1, 0.9 and 1.1, not raw quotes.

† Outside the quoted strikes for that expiry (2026-10-29 (110%); 2026-11-06 (110%)). Those cells are the fitted wing, not a traded vol.

| Expiry | Days | Quotes | SVI ATM | SVI 90% | SVI 110% | Skew (vol pts) | SVI RMSE (vol pts) | g(k) >= 0 |
|---|---|---|---|---|---|---|---|---|
| 2026-10-29 | 7 | 90 | 15.75% | 36.28% | 10.16%† | 26.12† | 0.60 | yes |
| 2026-11-06 | 15 | 130 | 15.84% | 30.52% | 10.88%† | 19.64† | 0.67 | yes |
| 2026-11-20 | 29 | 142 | 14.99% | 26.64% | 13.76% | 12.88 | 0.41 | yes |
| 2026-11-30 | 39 | 194 | 14.52% | 24.52% | 12.26% | 12.26 | 0.44 | yes |
| 2026-12-18 | 57 | 167 | 15.13% | 23.60% | 12.07% | 11.52 | 0.24 | yes |
| 2027-01-15 | 85 | 72 | 15.11% | 22.07% | 11.85% | 10.22 | 0.22 | yes |
| 2027-02-19 | 120 | 64 | 15.40% | 21.40% | 12.32% | 9.08 | 0.24 | yes |
| 2027-03-31 | 160 | 63 | 15.77% | 20.75% | 12.76% | 7.99 | 0.23 | yes |
| 2027-06-30 | 251 | 51 | 16.43% | 20.26% | 14.15% | 6.11 | 0.34 | yes |
| 2027-09-30 | 343 | 62 | 17.18% | 20.15% | 15.17% | 4.97 | 0.37 | yes |
| 2028-06-16 | 603 | 42 | 18.39% | 20.21% | 16.98% | 3.24 | 0.43 | yes |

### Greeks, 29-day expiry, strike 766, SVI vol 14.95%, call $12.67

Vega and rho are for a 1.00 move in vol or rate. Theta is per year.

| Greek | Call | Put |
|---|---|---|
| delta | 0.5037 | -0.4953 |
| gamma | 0.0124 | 0.0124 |
| vega | 85.8196 | 85.8196 |
| theta | -91.0051 | -69.6423 |
| rho | 29.5681 | -31.0980 |

## Data provenance

- **Option chain:** SPY calls and puts for 11 expiries
  (2026-10-29 to 2028-06-16), source: yfinance (Yahoo Finance), current chain snapshot; not historical.
  Snapshot taken 2026-10-23T05:01:11+00:00 (UTC). Quotes are last trades on the 2026-10-22 close.
- **Spot and rates:** SPY close 763.96; 13-week T-bill (^IRX) 4.02%;
  trailing-12-month dividends $9.414 from 5 payments (Yahoo Finance).
- **Frozen snapshot:** 23 files in `data/raw/` (22 chain CSVs plus `meta.json`),
  each SHA-256 hashed in `data/MANIFEST.json`. `make all` checks the hashes and fails if a file has changed.
- **Not historical:** Yahoo serves only the current chain, so this snapshot cannot be downloaded again.
  `make fetch` takes a new snapshot and changes the hashes and the results.
- **Terms:** the snapshot is in the repo so the study can be rerun. Check Yahoo's terms before using it for anything else.

## Method

- Rate 4.02% (13-week T-bill (^IRX), flat across maturities). Dividend yield 1.22%,
  log(1 + trailing-12-month dividends / spot). Forward F = S e^((r-q)T); log-moneyness k = ln(K/F).
  `meta.json` also stores the 10-year yield; the fit does not use it.
- Filters: last trade on 2026-10-22, price >= $0.05, volume > 0,
  out-of-the-money only, |k| <= 0.35, at least 5 days.
- IV: Brent on Black-Scholes-Merton. Prices outside the no-arbitrage bounds are dropped.
- SVI: raw total variance w(k) = a + b(rho(k-m) + sqrt((k-m)^2 + sigma^2)), least squares, one fit per expiry.
- The page recomputes prices, Greeks, SVI vols and the calendar grid in `web/src/volmath.js`.
  `web/tests/volmath.test.js` checks them against `results/summary.json`.

## Limits

- yfinance option chains are **current-only**: there is no historical chain, so this is one frozen snapshot
  (taken 2026-10-23T05:01:11+00:00 UTC) and cannot be downloaded again. `make fetch` would be a different date.
- The snapshot was taken outside market hours, so bid and ask were 0 for most contracts
  (165 of 3682 had a bid). IVs use last-trade prices, which are not
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
