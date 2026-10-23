// Browser versions of src/volsurf/{bs,svi}.py. tests/volmath.test.js checks them against results/summary.json.

// Cumulative normal, Hart (1968) double-precision algorithm as given by West (2005).
export function ncdf(x) {
  const z = Math.abs(x);
  let c;
  if (z > 37) c = 0;
  else {
    const e = Math.exp((-z * z) / 2);
    if (z < 7.07106781186547) {
      let n = 3.52624965998911e-2 * z + 0.700383064443688;
      n = n * z + 6.37396220353165; n = n * z + 33.912866078383; n = n * z + 112.079291497871;
      n = n * z + 221.213596169931; n = n * z + 220.206867912376;
      let d = 8.83883476483184e-2 * z + 1.75566716318264;
      d = d * z + 16.064177579207; d = d * z + 86.7807322029461; d = d * z + 296.564248779674;
      d = d * z + 637.333633378831; d = d * z + 793.826512519948; d = d * z + 440.413735824752;
      c = (e * n) / d;
    } else {
      let b = z + 0.65; b = z + 4 / b; b = z + 3 / b; b = z + 2 / b; b = z + 1 / b;
      c = e / b / 2.506628274631;
    }
  }
  return x > 0 ? 1 - c : c;
}
export const npdf = (x) => Math.exp((-x * x) / 2) / Math.sqrt(2 * Math.PI);

export function bsPrice(S, K, T, r, q, vol, kind = "call") {
  const d1 = (Math.log(S / K) + (r - q + 0.5 * vol * vol) * T) / (vol * Math.sqrt(T));
  const d2 = d1 - vol * Math.sqrt(T);
  const dq = Math.exp(-q * T), dr = Math.exp(-r * T);
  return kind === "call" ? S * dq * ncdf(d1) - K * dr * ncdf(d2) : K * dr * ncdf(-d2) - S * dq * ncdf(-d1);
}

export function greeks(S, K, T, r, q, vol, kind = "call") {
  const d1 = (Math.log(S / K) + (r - q + 0.5 * vol * vol) * T) / (vol * Math.sqrt(T));
  const d2 = d1 - vol * Math.sqrt(T);
  const dq = Math.exp(-q * T), dr = Math.exp(-r * T), p = npdf(d1);
  const gamma = (dq * p) / (S * vol * Math.sqrt(T));
  const vega = S * dq * p * Math.sqrt(T);
  const common = (-S * dq * p * vol) / (2 * Math.sqrt(T));
  if (kind === "call") {
    return { delta: dq * ncdf(d1), gamma, vega, theta: common - r * K * dr * ncdf(d2) + q * S * dq * ncdf(d1),
      rho: K * T * dr * ncdf(d2) };
  }
  return { delta: -dq * ncdf(-d1), gamma, vega, theta: common + r * K * dr * ncdf(-d2) - q * S * dq * ncdf(-d1),
    rho: -K * T * dr * ncdf(-d2) };
}

export function totalVar(k, { a, b, rho, m, sigma }) {
  return a + b * (rho * (k - m) + Math.sqrt((k - m) ** 2 + sigma ** 2));
}
export const sviVol = (k, p, T) => Math.sqrt(totalVar(k, p) / T);

export function gFunction(k, { a, b, rho, m, sigma }) {
  const x = k - m, rt = Math.sqrt(x * x + sigma * sigma);
  const w = a + b * (rho * x + rt), w1 = b * (rho + x / rt), w2 = (b * sigma * sigma) / rt ** 3;
  return (1 - (k * w1) / (2 * w)) ** 2 - ((w1 * w1) / 4) * (1 / w + 0.25) + w2 / 2;
}

export const linspace = (a, b, n) => Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));

export function calendarGrid(slices, grid) {
  // diff[i][j] = w_{i+1}(k_j) - w_i(k_j); negative = calendar arbitrage
  return slices.slice(1).map((s, i) => grid.map((k) => totalVar(k, s.svi) - totalVar(k, slices[i].svi)));
}

export function forward(S, r, q, T) {
  return S * Math.exp((r - q) * T);
}
